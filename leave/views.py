from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters
from datetime import datetime, date
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
import csv

from .models import LeaveType, LeaveRequest, LeaveBalance
from .serializers import (
	LeaveTypeSerializer, LeaveRequestSerializer, LeaveRequestApprovalSerializer,
	LeaveBalanceSerializer
)
from users.models import User
# Import notification utilities
try:
    from notifications.utils import send_leave_notification
except ImportError:
    # Fallback if notifications app is not available
    def send_leave_notification(*args, **kwargs):
        pass


class IsHRorManager(permissions.BasePermission):
	def has_permission(self, request, view):
		return request.user.is_authenticated and request.user.can_manage_attendance()


# Leave Types (HR/Admin)
class LeaveTypeListCreateView(generics.ListCreateAPIView):
	queryset = LeaveType.objects.all()
	serializer_class = LeaveTypeSerializer
	permission_classes = [permissions.IsAuthenticated, IsHRorManager]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ['name', 'description']
	ordering_fields = ['name', 'max_days_per_year', 'is_active']
	ordering = ['name']


class LeaveTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = LeaveType.objects.all()
	serializer_class = LeaveTypeSerializer
	permission_classes = [permissions.IsAuthenticated, IsHRorManager]


# Leave Requests
class LeaveRequestCreateView(generics.CreateAPIView):
	serializer_class = LeaveRequestSerializer
	permission_classes = [permissions.IsAuthenticated]

	def perform_create(self, serializer):
		leave_request = serializer.save(user=self.request.user)
		# Send notification
		send_leave_notification(leave_request, 'submitted')
	
	def get_serializer_context(self):
		context = super().get_serializer_context()
		context['request'] = self.request
		return context


class LeaveRequestListView(generics.ListAPIView):
	serializer_class = LeaveRequestSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [DjangoFilterBackend, filters.OrderingFilter] if DjangoFilterBackend else [filters.OrderingFilter]
	filterset_fields = ['leave_type', 'status', 'start_date', 'end_date'] if DjangoFilterBackend else []
	ordering_fields = ['start_date', 'end_date', 'created_at']
	ordering = ['-created_at']

	def get_queryset(self):
		user = self.request.user
		if user.can_manage_attendance():
			qs = LeaveRequest.objects.select_related('user', 'leave_type')
			user_id = self.request.query_params.get('user_id')
			if user_id:
				qs = qs.filter(user_id=user_id)
			return qs
		return LeaveRequest.objects.filter(user=user).select_related('leave_type')


class LeaveRequestDetailView(generics.RetrieveAPIView):
	serializer_class = LeaveRequestSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		user = self.request.user
		if user.can_manage_attendance():
			return LeaveRequest.objects.all()
		return LeaveRequest.objects.filter(user=user)


class LeaveApprovalView(APIView):
	permission_classes = [permissions.IsAuthenticated, IsHRorManager]

	def post(self, request, pk):
		try:
			leave = LeaveRequest.objects.get(pk=pk)
		except LeaveRequest.DoesNotExist:
			return Response({'error': 'Leave request not found'}, status=404)

		if leave.status not in ['pending']:
			return Response({'error': 'Leave request has already been processed'}, status=400)

		serializer = LeaveRequestApprovalSerializer(data=request.data)
		if serializer.is_valid():
			new_status = serializer.validated_data['status']
			approval_notes = serializer.validated_data.get('approval_notes', '')
			
			# Store original status for rollback if needed
			original_status = leave.status
			
			leave.status = new_status
			leave.approval_notes = approval_notes
			leave.approved_by = request.user
			leave.approved_at = timezone.now()
			
			try:
				leave.save()
				# Send notification
				send_leave_notification(leave, new_status)
				return Response({
					'message': f"Leave request {new_status} successfully",
					'leave': LeaveRequestSerializer(leave).data
				})
			except Exception as e:
				# Rollback on error
				leave.status = original_status
				leave.approved_by = None
				leave.approved_at = None
				return Response({'error': str(e)}, status=400)
		
		return Response(serializer.errors, status=400)


# Leave Balances
class LeaveBalanceListView(generics.ListAPIView):
	serializer_class = LeaveBalanceSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [DjangoFilterBackend] if DjangoFilterBackend else []
	filterset_fields = ['user', 'leave_type', 'year'] if DjangoFilterBackend else []

	def get_queryset(self):
		user = self.request.user
		if user.can_manage_attendance():
			qs = LeaveBalance.objects.select_related('user', 'leave_type')
			user_id = self.request.query_params.get('user_id')
			if user_id:
				qs = qs.filter(user_id=user_id)
			return qs
		return LeaveBalance.objects.filter(user=user).select_related('leave_type')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_leave_requests(request):
	qs = LeaveRequest.objects.filter(user=request.user).select_related('leave_type')
	return Response(LeaveRequestSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsHRorManager])
def allocate_leave_balance(request):
	user_id = request.data.get('user')
	leave_type_id = request.data.get('leave_type')
	year = request.data.get('year')
	total_allocated = request.data.get('total_allocated')
	
	if not all([user_id, leave_type_id, year, total_allocated]):
		return Response({'error': 'user, leave_type, year, total_allocated are required'}, status=400)
	
	try:
		user = User.objects.get(id=user_id)
		leave_type = LeaveType.objects.get(id=leave_type_id)
	except (User.DoesNotExist, LeaveType.DoesNotExist):
		return Response({'error': 'Invalid user or leave type'}, status=400)
	
	lb, created = LeaveBalance.objects.get_or_create(
		user_id=user_id, leave_type_id=leave_type_id, year=year,
		defaults={'total_allocated': total_allocated}
	)
	if not created:
		lb.total_allocated = total_allocated
		lb.save()
	
	return Response({
		'message': f'Leave balance {"created" if created else "updated"} for {user.get_full_name()}',
		'balance': LeaveBalanceSerializer(lb).data
	})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsHRorManager])
def bulk_allocate_leave(request):
	"""Allocate leave for all active employees for a specific year"""
	year = request.data.get('year', date.today().year)
	
	allocated_count = LeaveBalance.allocate_annual_leave(year)
	
	return Response({
		'message': f'Leave balances allocated for {allocated_count} employee-leave type combinations for year {year}',
		'allocated_count': allocated_count,
		'year': year
	})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def leave_calendar(request):
	"""Get leave calendar view for current user or all users (HR/Admin)"""
	year = request.query_params.get('year', date.today().year)
	month = request.query_params.get('month')
	user_id = request.query_params.get('user_id')
	
	# Build query filters
	filters = Q(status='approved')
	
	if year:
		filters &= Q(start_date__year=year)
	if month:
		filters &= Q(start_date__month=month)
	
	# Role-based access control
	if request.user.can_manage_attendance():
		if user_id:
			filters &= Q(user_id=user_id)
		queryset = LeaveRequest.objects.filter(filters)
	else:
		filters &= Q(user=request.user)
		queryset = LeaveRequest.objects.filter(filters)
	
	leave_requests = queryset.select_related('user', 'leave_type').order_by('start_date')
	
	# Format for calendar display
	calendar_data = []
	for leave in leave_requests:
		calendar_data.append({
			'id': leave.id,
			'title': f"{leave.user.get_full_name()} - {leave.leave_type.name}",
			'start': leave.start_date.isoformat(),
			'end': leave.end_date.isoformat(),
			'user': leave.user.get_full_name(),
			'employee_id': leave.user.employee_id,
			'leave_type': leave.leave_type.name,
			'total_days': leave.total_days,
			'is_paid': leave.leave_type.is_paid
		})
	
	return Response({
		'calendar_events': calendar_data,
		'total_events': len(calendar_data),
		'filters': {
			'year': year,
			'month': month,
			'user_id': user_id
		}
	})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsHRorManager])
def leave_statistics(request):
	"""Get comprehensive leave statistics"""
	year = request.query_params.get('year', date.today().year)
	department = request.query_params.get('department')
	
	# Base queryset
	leave_requests = LeaveRequest.objects.filter(start_date__year=year)
	users = User.objects.filter(is_active=True)
	
	if department:
		leave_requests = leave_requests.filter(user__department=department)
		users = users.filter(department=department)
	
	# Statistics calculations
	stats = {
		'total_employees': users.count(),
		'total_leave_requests': leave_requests.count(),
		'approved_requests': leave_requests.filter(status='approved').count(),
		'pending_requests': leave_requests.filter(status='pending').count(),
		'rejected_requests': leave_requests.filter(status='rejected').count(),
		'total_leave_days': leave_requests.filter(status='approved').aggregate(
			total=Sum('total_days')
		)['total'] or 0,
	}
	
	# Leave type breakdown
	leave_type_stats = leave_requests.filter(status='approved').values(
		'leave_type__name'
	).annotate(
		count=Count('id'),
		total_days=Sum('total_days')
	).order_by('-total_days')
	
	# Department breakdown (if not filtered by department)
	department_stats = []
	if not department:
		department_stats = leave_requests.filter(status='approved').values(
			'user__department'
		).annotate(
			count=Count('id'),
			total_days=Sum('total_days')
		).order_by('-total_days')
	
	# Monthly breakdown
	monthly_stats = []
	for month in range(1, 13):
		month_requests = leave_requests.filter(
			start_date__month=month,
			status='approved'
		)
		monthly_stats.append({
			'month': month,
			'month_name': date(year, month, 1).strftime('%B'),
			'requests': month_requests.count(),
			'total_days': month_requests.aggregate(total=Sum('total_days'))['total'] or 0
		})
	
	return Response({
		'summary': stats,
		'leave_type_breakdown': list(leave_type_stats),
		'department_breakdown': list(department_stats),
		'monthly_breakdown': monthly_stats,
		'year': year,
		'department': department
	})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsHRorManager])
def leave_reports(request):
	"""Generate and export leave reports"""
	export_format = request.query_params.get('format', 'json')
	year = request.query_params.get('year', date.today().year)
	month = request.query_params.get('month')
	department = request.query_params.get('department')
	status_filter = request.query_params.get('status')
	
	# Build queryset
	queryset = LeaveRequest.objects.select_related('user', 'leave_type', 'approved_by')
	
	filters = Q(start_date__year=year)
	if month:
		filters &= Q(start_date__month=month)
	if department:
		filters &= Q(user__department=department)
	if status_filter:
		filters &= Q(status=status_filter)
	
	leave_requests = queryset.filter(filters).order_by('-start_date')
	
	if export_format == 'csv':
		response = HttpResponse(content_type='text/csv')
		response['Content-Disposition'] = f'attachment; filename="leave_report_{year}.csv"'
		
		writer = csv.writer(response)
		writer.writerow([
			'Employee ID', 'Employee Name', 'Department', 'Leave Type',
			'Start Date', 'End Date', 'Total Days', 'Status', 'Approved By',
			'Approved At', 'Reason', 'Emergency Contact', 'Emergency Phone'
		])
		
		for leave in leave_requests:
			writer.writerow([
				leave.user.employee_id,
				leave.user.get_full_name(),
				leave.user.department,
				leave.leave_type.name,
				leave.start_date,
				leave.end_date,
				leave.total_days,
				leave.status.title(),
				leave.approved_by.get_full_name() if leave.approved_by else '',
				leave.approved_at.strftime('%Y-%m-%d %H:%M') if leave.approved_at else '',
				leave.reason,
				leave.emergency_contact,
				leave.emergency_phone
			])
		
		return response
	
	# JSON response
	serializer = LeaveRequestSerializer(leave_requests, many=True)
	return Response({
		'leave_requests': serializer.data,
		'total_records': leave_requests.count(),
		'filters': {
			'year': year,
			'month': month,
			'department': department,
			'status': status_filter
		}
	})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_leave_request(request, pk):
	"""Allow employees to cancel their own pending leave requests"""
	try:
		leave_request = LeaveRequest.objects.get(pk=pk)
	except LeaveRequest.DoesNotExist:
		return Response({'error': 'Leave request not found'}, status=404)
	
	# Check permissions
	if leave_request.user != request.user and not request.user.can_manage_attendance():
		return Response({'error': 'Permission denied'}, status=403)
	
	# Only allow cancellation of pending requests
	if leave_request.status != 'pending':
		return Response({'error': 'Can only cancel pending leave requests'}, status=400)
	
	leave_request.status = 'cancelled'
	leave_request.save()
	
	return Response({
		'message': 'Leave request cancelled successfully',
		'leave': LeaveRequestSerializer(leave_request).data
	})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsHRorManager])
def bulk_leave_actions(request):
	"""Perform bulk actions on multiple leave requests"""
	leave_ids = request.data.get('leave_ids', [])
	action = request.data.get('action')  # approve, reject, delete
	approval_notes = request.data.get('approval_notes', '')
	
	if not leave_ids or not action:
		return Response({'error': 'leave_ids and action are required'}, status=400)
	
	if action not in ['approve', 'reject', 'delete']:
		return Response({'error': 'Invalid action. Must be approve, reject, or delete'}, status=400)
	
	leave_requests = LeaveRequest.objects.filter(id__in=leave_ids)
	
	if not leave_requests.exists():
		return Response({'error': 'No leave requests found with provided IDs'}, status=404)
	
	updated_count = 0
	errors = []
	
	for leave in leave_requests:
		try:
			if action in ['approve', 'reject']:
				if leave.status != 'pending':
					errors.append(f'Leave request {leave.id} is not in pending status')
					continue
				
				leave.status = 'approved' if action == 'approve' else 'rejected'
				leave.approved_by = request.user
				leave.approved_at = timezone.now()
				leave.approval_notes = approval_notes
				leave.save()
				updated_count += 1
			
			elif action == 'delete':
				leave.delete()
				updated_count += 1
		
		except Exception as e:
			errors.append(f'Error processing leave request {leave.id}: {str(e)}')
	
	return Response({
		'message': f'{updated_count} leave requests {action}d successfully',
		'updated_count': updated_count,
		'errors': errors
	})


# Web Views for Leave Management
@login_required
def leave_dashboard(request):
	"""Dashboard view for leave management"""
	user = request.user
	
	# Get pending requests
	pending_requests = LeaveRequest.objects.filter(
		user=user, 
		status='pending'
	).order_by('-created_at')
	
	# Get upcoming approved leaves
	upcoming_leaves = LeaveRequest.objects.filter(
		user=user,
		status='approved',
		start_date__gte=timezone.now().date()
	).order_by('start_date')
	
	# Get leave balances
	leave_balances = LeaveBalance.objects.filter(
		user=user,
		year=timezone.now().year
	).select_related('leave_type')
	
	# For managers - get team pending requests
	team_pending = None
	team_on_leave = None
	if user.can_manage_attendance():
		team_pending = LeaveRequest.objects.filter(
			user__manager=user,
			status='pending'
		).order_by('-created_at')
		
		team_on_leave = LeaveRequest.objects.filter(
			user__manager=user,
			status='approved',
			start_date__lte=timezone.now().date(),
			end_date__gte=timezone.now().date()
		)
	
	# Recent activity (placeholder - would need activity tracking)
	recent_activity = []
	
	context = {
		'pending_requests': pending_requests,
		'upcoming_leaves': upcoming_leaves,
		'leave_balances': leave_balances,
		'team_pending': team_pending,
		'team_on_leave': team_on_leave,
		'recent_activity': recent_activity,
	}
	
	return render(request, 'leave/leave_dashboard.html', context)


@login_required
def team_requests_web(request):
    """Web-based team leave requests view for managers"""
    user = request.user
    
    # Check if user can manage team requests
    if not user.can_manage_attendance():
        return render(request, 'leave/access_denied.html')
    
    # Get query parameters
    status_filter = request.GET.get('status', 'pending')
    employee_filter = request.GET.get('employee')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build queryset for team requests
    queryset = LeaveRequest.objects.filter(user__manager=user)
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if employee_filter:
        queryset = queryset.filter(user_id=employee_filter)
    
    if date_from:
        queryset = queryset.filter(start_date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(end_date__lte=date_to)
    
    # Order by creation date
    queryset = queryset.order_by('-created_at').select_related('user', 'leave_type')
    
    # Paginate results
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    leave_requests = paginator.get_page(page_number)
    
    # Get team members for filter dropdown
    team_members = user.managed_team.all() if hasattr(user, 'managed_team') else []
    
    # Get summary statistics
    summary_stats = {
        'pending': LeaveRequest.objects.filter(user__manager=user, status='pending').count(),
        'approved': LeaveRequest.objects.filter(user__manager=user, status='approved').count(),
        'rejected': LeaveRequest.objects.filter(user__manager=user, status='rejected').count(),
        'total': LeaveRequest.objects.filter(user__manager=user).count(),
    }
    
    context = {
        'leave_requests': leave_requests,
        'team_members': team_members,
        'summary_stats': summary_stats,
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'date_from': date_from,
        'date_to': date_to,
        'today': timezone.now().date(),
    }
    
    return render(request, 'leave/team_requests.html', context)


@login_required
def leave_requests_web(request):
    """Web-based leave requests view for all users"""
    user = request.user
    
    # Get query parameters
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build queryset - users see their own requests, managers see team requests
    if user.can_manage_attendance():
        queryset = LeaveRequest.objects.filter(user__manager=user)
    else:
        queryset = LeaveRequest.objects.filter(user=user)
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if date_from:
        queryset = queryset.filter(start_date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(end_date__lte=date_to)
    
    # Order by creation date
    queryset = queryset.order_by('-created_at').select_related('user', 'leave_type')
    
    # Paginate results
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page')
    leave_requests = paginator.get_page(page_number)
    
    # Get summary statistics
    summary_stats = {
        'pending': queryset.filter(status='pending').count(),
        'approved': queryset.filter(status='approved').count(),
        'rejected': queryset.filter(status='rejected').count(),
        'total': queryset.count(),
    }
    
    context = {
        'leave_requests': leave_requests,
        'summary_stats': summary_stats,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'today': timezone.now().date(),
        'is_manager': user.can_manage_attendance(),
    }
    
    return render(request, 'leave/requests_list.html', context)


@login_required
def leave_calendar_web(request):
    """Web-based leave calendar view"""
    user = request.user
    
    # Get query parameters
    year = request.GET.get('year', timezone.now().year)
    month = request.GET.get('month', timezone.now().month)
    
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = timezone.now().year
        month = timezone.now().month
    
    # Get leave requests for the specified month/year
    if user.can_manage_attendance():
        # Managers see team leave requests
        leave_requests = LeaveRequest.objects.filter(
            user__manager=user,
            status='approved',
            start_date__year=year,
            start_date__month=month
        ).select_related('user', 'leave_type')
    else:
        # Regular users see their own requests
        leave_requests = LeaveRequest.objects.filter(
            user=user,
            start_date__year=year,
            start_date__month=month
        ).select_related('leave_type')
    
    # Get upcoming leave requests (next 30 days)
    if user.can_manage_attendance():
        # For managers, get team members' upcoming leaves
        from users.models import User
        team_members = User.objects.filter(manager=user)
        upcoming_leaves = LeaveRequest.objects.filter(
            user__in=team_members,
            status='approved',
            start_date__gte=timezone.now().date(),
            start_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        ).select_related('user', 'leave_type')[:10]
    else:
        # For regular users, get their own upcoming leaves
        upcoming_leaves = LeaveRequest.objects.filter(
            user=user,
            status='approved',
            start_date__gte=timezone.now().date(),
            start_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        ).select_related('leave_type')[:10]
    
    context = {
        'leave_requests': leave_requests,
        'upcoming_leaves': upcoming_leaves,
        'current_year': year,
        'current_month': month,
        'today': timezone.now().date(),
        'is_manager': user.can_manage_attendance(),
    }
    
    return render(request, 'leave/calendar.html', context)


class LeaveRequestEditView(LoginRequiredMixin, UpdateView):
	"""View for editing leave requests"""
	model = LeaveRequest
	fields = ['leave_type', 'start_date', 'end_date', 'reason']
	template_name = 'leave/request_edit.html'
	success_url = reverse_lazy('leave:leave_dashboard')
	
	def get_queryset(self):
		# Users can only edit their own pending requests
		return LeaveRequest.objects.filter(
			user=self.request.user,
			status='pending'
		)
	
	def form_valid(self, form):
		messages.success(self.request, 'Leave request updated successfully.')
		return super().form_valid(form)
