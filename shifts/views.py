from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta, date
import json
from .models import Shift, ShiftSchedule, ShiftTemplate
from .serializers import (
    ShiftSerializer, ShiftScheduleSerializer, 
    ShiftTemplateSerializer,
    ShiftScheduleCreateSerializer, ShiftScheduleUpdateSerializer,
    ShiftBulkCreateSerializer, ShiftConflictSerializer,
    ShiftReportSerializer, ShiftSummarySerializer
)
from users.permissions import IsManagerOrHR, IsEmployeeOrManagerOrHR
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters

# Import notification utilities
try:
    from notifications.utils import send_shift_notification
except ImportError:
    # Fallback if notifications app is not available
    def send_shift_notification(*args, **kwargs):
        pass


class ShiftListView(generics.ListCreateAPIView):
    """List and create shifts"""
    queryset = Shift.objects.filter(is_active=True)
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHR]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active'] if DjangoFilterBackend else []
    search_fields = ['name']
    ordering_fields = ['name', 'start_time', 'end_time', 'created_at']
    ordering = ['name']


class ShiftDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete a shift"""
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHR]

    def perform_destroy(self, instance):
        """Soft delete by setting is_active to False"""
        instance.is_active = False
        instance.save()


class ShiftTemplateListView(generics.ListCreateAPIView):
    """List and create shift templates"""
    queryset = ShiftTemplate.objects.filter(is_active=True)
    serializer_class = ShiftTemplateSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHR]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['frequency', 'is_active', 'shift'] if DjangoFilterBackend else []
    search_fields = ['name']
    ordering_fields = ['name', 'start_date', 'created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)


class ShiftTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete a shift template"""
    queryset = ShiftTemplate.objects.all()
    serializer_class = ShiftTemplateSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHR]

    def perform_destroy(self, instance):
        """Soft delete by setting is_active to False"""
        instance.is_active = False
        instance.save()


class ShiftScheduleListView(generics.ListCreateAPIView):
    """List and create shift schedules"""
    serializer_class = ShiftScheduleSerializer
    permission_classes = [IsAuthenticated, IsEmployeeOrManagerOrHR]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'shift', 'employee', 'date', 'template'] if DjangoFilterBackend else []
    search_fields = ['notes']
    ordering_fields = ['date', 'shift__start_time', 'created_at']
    ordering = ['-date', 'shift__start_time']

    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.role in ['manager', 'hr']:
            return ShiftSchedule.objects.all()
        else:
            return ShiftSchedule.objects.filter(employee=user)

    def get_serializer_class(self):
        """Use different serializer for creation"""
        if self.request.method == 'POST':
            return ShiftScheduleCreateSerializer
        return ShiftScheduleSerializer

    def perform_create(self, serializer):
        """Set created_by to current user"""
        shift_schedule = serializer.save(created_by=self.request.user)
        # Send notification
        send_shift_notification(shift_schedule, 'assigned')


class ShiftScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete a shift schedule"""
    queryset = ShiftSchedule.objects.all()
    serializer_class = ShiftScheduleSerializer
    permission_classes = [IsAuthenticated, IsEmployeeOrManagerOrHR]

    def get_queryset(self):
        """Filter based on user role"""
        user = self.request.user
        if user.role in ['manager', 'hr']:
            return ShiftSchedule.objects.all()
        else:
            return ShiftSchedule.objects.filter(employee=user)

    def get_serializer_class(self):
        """Use different serializer for updates"""
        if self.request.method in ['PUT', 'PATCH']:
            return ShiftScheduleUpdateSerializer
        return ShiftScheduleSerializer


class ShiftBulkCreateView(generics.CreateAPIView):
    """Bulk create shift schedules"""
    serializer_class = ShiftBulkCreateSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHR]

    def create(self, request, *args, **kwargs):
        """Create multiple shift schedules"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        employee_ids = data['employee_ids']
        shift_id = data['shift_id']
        start_date = data['start_date']
        end_date = data['end_date']
        template_id = data.get('template_id')
        notes = data.get('notes', '')
        
        # Check for conflicts
        conflicts = self._check_conflicts(employee_ids, start_date, end_date)
        if conflicts:
            return Response({
                'message': 'Conflicts detected',
                'conflicts': conflicts
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create schedules
        created_schedules = []
        current_date = start_date
        
        while current_date <= end_date:
            for employee_id in employee_ids:
                schedule = ShiftSchedule.objects.create(
                    employee_id=employee_id,
                    shift_id=shift_id,
                    date=current_date,
                    template_id=template_id,
                    notes=notes,
                    created_by=request.user
                )
                created_schedules.append(schedule)
            
            # Move to next date based on frequency
            if template_id:
                template = ShiftTemplate.objects.get(id=template_id)
                if template.frequency == 'daily':
                    current_date += timedelta(days=1)
                elif template.frequency == 'weekly':
                    current_date += timedelta(days=7)
                elif template.frequency == 'monthly':
                    # Simple monthly increment (approximate)
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
            else:
                current_date += timedelta(days=1)
        
        # Serialize created schedules
        result_serializer = ShiftScheduleSerializer(created_schedules, many=True)
        return Response({
            'message': f'Successfully created {len(created_schedules)} shift schedules',
            'schedules': result_serializer.data
        }, status=status.HTTP_201_CREATED)

    def _check_conflicts(self, employee_ids, start_date, end_date):
        """Check for scheduling conflicts"""
        conflicts = []
        
        for employee_id in employee_ids:
            # Check for existing shifts
            existing_shifts = ShiftSchedule.objects.filter(
                employee_id=employee_id,
                date__range=[start_date, end_date]
            )
            
            for shift in existing_shifts:
                conflicts.append({
                    'employee_id': employee_id,
                    'employee_name': shift.employee.get_full_name(),
                    'conflict_date': shift.date,
                    'conflict_type': 'shift',
                    'existing_record': f"Shift: {shift.shift.name}"
                })
            
            # Check for attendance records
            from attendance.models import Attendance
            existing_attendance = Attendance.objects.filter(
                employee_id=employee_id,
                date__range=[start_date, end_date]
            )
            
            for attendance in existing_attendance:
                conflicts.append({
                    'employee_id': employee_id,
                    'employee_name': attendance.employee.get_full_name(),
                    'conflict_date': attendance.date,
                    'conflict_type': 'attendance',
                    'existing_record': f"Attendance: {attendance.status}"
                })
        
        return conflicts


class ShiftConflictCheckView(generics.CreateAPIView):
    """Check for scheduling conflicts"""
    serializer_class = ShiftBulkCreateSerializer
    permission_classes = [IsAuthenticated, IsManagerOrHR]

    def create(self, request, *args, **kwargs):
        """Check for conflicts without creating schedules"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        employee_ids = data['employee_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        
        conflicts = self._check_conflicts(employee_ids, start_date, end_date)
        
        return Response({
            'has_conflicts': len(conflicts) > 0,
            'conflict_count': len(conflicts),
            'conflicts': conflicts
        }, status=status.HTTP_200_OK)

    def _check_conflicts(self, employee_ids, start_date, end_date):
        """Check for scheduling conflicts"""
        conflicts = []
        
        for employee_id in employee_ids:
            # Check for existing shifts
            existing_shifts = ShiftSchedule.objects.filter(
                employee_id=employee_id,
                date__range=[start_date, end_date]
            )
            
            for shift in existing_shifts:
                conflicts.append({
                    'employee_id': employee_id,
                    'employee_name': shift.employee.get_full_name(),
                    'conflict_date': shift.date,
                    'conflict_type': 'shift',
                    'existing_record': f"Shift: {shift.shift.name}"
                })
            
            # Check for attendance records
            from attendance.models import Attendance
            existing_attendance = Attendance.objects.filter(
                employee_id=employee_id,
                date__range=[start_date, end_date]
            )
            
            for attendance in existing_attendance:
                conflicts.append({
                    'employee_id': employee_id,
                    'employee_name': attendance.employee.get_full_name(),
                    'conflict_date': attendance.date,
                    'conflict_type': 'attendance',
                    'existing_record': f"Attendance: {attendance.status}"
                })
        
        return conflicts


class ShiftReportView(generics.ListAPIView):
    """Generate shift reports"""
    permission_classes = [IsAuthenticated, IsManagerOrHR]
    serializer_class = ShiftReportSerializer

    def get(self, request, *args, **kwargs):
        """Generate comprehensive shift report"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            # Default to current month
            today = timezone.now().date()
            start_date = today.replace(day=1)
            # Simple month end calculation
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        # Convert to date objects
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get shift data
        shifts = ShiftSchedule.objects.filter(
            date__range=[start_date, end_date]
        )
        
        # Calculate statistics
        total_shifts = shifts.count()
        completed_shifts = shifts.filter(status='completed').count()
        cancelled_shifts = shifts.filter(status='cancelled').count()
        no_show_shifts = shifts.filter(status='no_show').count()
        
        # Calculate total hours
        total_hours = sum(shift.shift.total_hours for shift in shifts if shift.shift.total_hours)
        average_hours = total_hours / total_shifts if total_shifts > 0 else 0
        
        # Get unique employees
        employee_count = shifts.values('employee').distinct().count()
        
        report_data = {
            'total_shifts': total_shifts,
            'completed_shifts': completed_shifts,
            'cancelled_shifts': cancelled_shifts,
            'no_show_shifts': no_show_shifts,
            'total_hours': round(total_hours, 2),
            'average_hours_per_shift': round(average_hours, 2),
            'date_range': f"{start_date} to {end_date}",
            'employee_count': employee_count
        }
        
        serializer = self.get_serializer(report_data)
        return Response(serializer.data)


class ShiftSummaryView(generics.ListAPIView):
    """Get shift summary for dashboard"""
    permission_classes = [IsAuthenticated, IsEmployeeOrManagerOrHR]
    serializer_class = ShiftSummarySerializer

    def get(self, request, *args, **kwargs):
        """Get shift summary"""
        today = timezone.now().date()
        
        # Filter based on user role
        if request.user.role in ['manager', 'hr']:
            today_shifts = ShiftSchedule.objects.filter(date=today).count()
            upcoming_shifts = ShiftSchedule.objects.filter(
                date__gt=today,
                status='scheduled'
            ).count()
            overdue_shifts = ShiftSchedule.objects.filter(
                date__lt=today,
                status='scheduled'
            ).count()
            active_employees = ShiftSchedule.objects.filter(
                date=today
            ).values('employee').distinct().count()
        else:
            today_shifts = ShiftSchedule.objects.filter(
                employee=request.user,
                date=today
            ).count()
            upcoming_shifts = ShiftSchedule.objects.filter(
                employee=request.user,
                date__gt=today,
                status='scheduled'
            ).count()
            overdue_shifts = ShiftSchedule.objects.filter(
                employee=request.user,
                date__lt=today,
                status='scheduled'
            ).count()
            active_employees = 1 if today_shifts > 0 else 0
        
        # Calculate total hours for today
        today_schedules = ShiftSchedule.objects.filter(date=today)
        total_hours_today = sum(
            schedule.shift.total_hours 
            for schedule in today_schedules 
            if schedule.shift.total_hours
        )
        
        summary_data = {
            'today_shifts': today_shifts,
            'upcoming_shifts': upcoming_shifts,
            'overdue_shifts': overdue_shifts,
            'active_employees': active_employees,
            'total_hours_today': round(total_hours_today, 2)
        }
        
        serializer = self.get_serializer(summary_data)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmployeeOrManagerOrHR])
def start_shift(request, pk):
    """Start a shift (mark as in progress)"""
    try:
        schedule = ShiftSchedule.objects.get(pk=pk)
        
        # Check permissions
        if request.user.role not in ['manager', 'hr'] and schedule.employee != request.user:
            return Response(
                {'error': 'You can only start your own shifts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if schedule.start_shift():
            serializer = ShiftScheduleSerializer(schedule)
            return Response({
                'message': 'Shift started successfully',
                'schedule': serializer.data
            })
        else:
            return Response({
                'error': 'Cannot start shift at this time or invalid status'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except ShiftSchedule.DoesNotExist:
        return Response(
            {'error': 'Shift schedule not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmployeeOrManagerOrHR])
def complete_shift(request, pk):
    """Complete a shift (mark as completed)"""
    try:
        schedule = ShiftSchedule.objects.get(pk=pk)
        
        # Check permissions
        if request.user.role not in ['manager', 'hr'] and schedule.employee != request.user:
            return Response(
                {'error': 'You can only complete your own shifts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if schedule.complete_shift():
            serializer = ShiftScheduleSerializer(schedule)
            return Response({
                'message': 'Shift completed successfully',
                'schedule': serializer.data
            })
        else:
            return Response({
                'error': 'Cannot complete shift with current status'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except ShiftSchedule.DoesNotExist:
        return Response(
            {'error': 'Shift schedule not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrHR])
def cancel_shift(request, pk):
    """Cancel a shift"""
    try:
        schedule = ShiftSchedule.objects.get(pk=pk)
        
        if schedule.cancel_shift():
            serializer = ShiftScheduleSerializer(schedule)
            return Response({
                'message': 'Shift cancelled successfully',
                'schedule': serializer.data
            })
        else:
            return Response({
                'error': 'Cannot cancel shift with current status'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except ShiftSchedule.DoesNotExist:
        return Response(
            {'error': 'Shift schedule not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployeeOrManagerOrHR])
def my_shifts(request):
    """Get current user's shifts"""
    user = request.user
    
    # Get query parameters
    status_filter = request.query_params.get('status')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    
    # Build queryset
    shifts = ShiftSchedule.objects.filter(employee=user)
    
    if status_filter:
        shifts = shifts.filter(status=status_filter)
    
    if date_from:
        shifts = shifts.filter(date__gte=date_from)
    
    if date_to:
        shifts = shifts.filter(date__lte=date_to)
    
    # Order by date
    shifts = shifts.order_by('date', 'shift__start_time')
    
    serializer = ShiftScheduleSerializer(shifts, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployeeOrManagerOrHR])
def shift_calendar(request):
    """Get shift calendar view"""
    year = request.query_params.get('year', timezone.now().year)
    month = request.query_params.get('month')
    employee_id = request.query_params.get('employee_id')
    
    # Build query filters
    filters = Q()
    
    if year:
        filters &= Q(date__year=year)
    if month:
        filters &= Q(date__month=month)
    
    # Role-based access control
    if request.user.role in ['manager', 'hr']:
        if employee_id:
            filters &= Q(employee_id=employee_id)
        queryset = ShiftSchedule.objects.filter(filters)
    else:
        filters &= Q(employee=request.user)
        queryset = ShiftSchedule.objects.filter(filters)
    
    schedules = queryset.select_related('employee', 'shift').order_by('date', 'shift__start_time')
    
    # Format for calendar display
    calendar_data = []
    for schedule in schedules:
        calendar_data.append({
            'id': schedule.id,
            'title': f"{schedule.employee.get_full_name()} - {schedule.shift.name}",
            'start': f"{schedule.date}T{schedule.shift.start_time}",
            'end': f"{schedule.date}T{schedule.shift.end_time}",
            'employee': schedule.employee.get_full_name(),
            'employee_id': schedule.employee.employee_id,
            'shift_name': schedule.shift.name,
            'status': schedule.status,
            'hours': schedule.shift.total_hours,
            'backgroundColor': _get_status_color(schedule.status),
            'borderColor': _get_status_color(schedule.status)
        })
    
    return Response({
        'calendar_events': calendar_data,
        'total_events': len(calendar_data),
        'filters': {
            'year': year,
            'month': month,
            'employee_id': employee_id
        }
    })


def _get_status_color(status):
    """Get color for shift status"""
    colors = {
        'scheduled': '#3498db',  # Blue
        'in_progress': '#f39c12',  # Orange
        'completed': '#27ae60',  # Green
        'cancelled': '#e74c3c',  # Red
        'no_show': '#95a5a6'  # Gray
    }
    return colors.get(status, '#3498db')


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrHR])
def create_shift_template_schedules(request):
    """Create shift schedules from a template"""
    template_id = request.data.get('template_id')
    employee_ids = request.data.get('employee_ids', [])
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')
    
    if not template_id:
        return Response({'error': 'Template ID is required'}, status=400)
    
    try:
        template = ShiftTemplate.objects.get(id=template_id)
    except ShiftTemplate.DoesNotExist:
        return Response({'error': 'Template not found'}, status=404)
    
    if not start_date:
        start_date = template.start_date
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = template.end_date or start_date + timedelta(days=30)
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate schedules based on template frequency
    created_schedules = []
    current_date = start_date
    
    while current_date <= end_date:
        for employee_id in employee_ids:
            # Check for conflicts
            existing = ShiftSchedule.objects.filter(
                employee_id=employee_id,
                date=current_date
            ).exists()
            
            if not existing:
                schedule = ShiftSchedule.objects.create(
                    employee_id=employee_id,
                    shift=template.shift,
                    date=current_date,
                    template=template,
                    created_by=request.user
                )
                created_schedules.append(schedule)
        
        # Move to next date based on frequency
        if template.frequency == 'daily':
            current_date += timedelta(days=1)
        elif template.frequency == 'weekly':
            current_date += timedelta(days=7)
        elif template.frequency == 'monthly':
            # Simple monthly increment
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        else:
            break  # Unknown frequency
    
    serializer = ShiftScheduleSerializer(created_schedules, many=True)
    return Response({
        'message': f'Created {len(created_schedules)} shift schedules from template',
        'schedules': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmployeeOrManagerOrHR])
def request_shift_swap(request):
    """Request to swap shifts with another employee"""
    schedule_id = request.data.get('schedule_id')
    target_employee_id = request.data.get('target_employee_id')
    reason = request.data.get('reason', '')
    
    try:
        schedule = ShiftSchedule.objects.get(id=schedule_id)
    except ShiftSchedule.DoesNotExist:
        return Response({'error': 'Shift schedule not found'}, status=404)
    
    # Check permissions
    if request.user.role not in ['manager', 'hr'] and schedule.employee != request.user:
        return Response({'error': 'You can only request swaps for your own shifts'}, status=403)
    
    # Check if target employee has availability
    from users.models import User
    try:
        target_employee = User.objects.get(id=target_employee_id)
    except User.DoesNotExist:
        return Response({'error': 'Target employee not found'}, status=404)
    
    # Check for conflicts
    existing_shift = ShiftSchedule.objects.filter(
        employee=target_employee,
        date=schedule.date
    ).exists()
    
    if existing_shift:
        return Response({
            'error': 'Target employee already has a shift on this date'
        }, status=400)
    
    # Create swap request (this would typically be a separate model)
    # For now, we'll add a note to the schedule
    schedule.notes = f"Swap requested with {target_employee.get_full_name()}. Reason: {reason}"
    schedule.save()
    
    return Response({
        'message': 'Shift swap request created',
        'schedule': ShiftScheduleSerializer(schedule).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsManagerOrHR])
def shift_coverage_report(request):
    """Get shift coverage report for a specific period"""
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    if not start_date or not end_date:
        # Default to current week
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get all shifts in the period
    schedules = ShiftSchedule.objects.filter(
        date__range=[start_date, end_date]
    ).select_related('employee', 'shift')
    
    # Group by date and shift
    coverage = {}
    current_date = start_date
    
    while current_date <= end_date:
        coverage[current_date.isoformat()] = {
            'date': current_date,
            'shifts': {},
            'total_employees': 0,
            'total_hours': 0
        }
        current_date += timedelta(days=1)
    
    # Populate coverage data
    for schedule in schedules:
        date_key = schedule.date.isoformat()
        shift_name = schedule.shift.name
        
        if shift_name not in coverage[date_key]['shifts']:
            coverage[date_key]['shifts'][shift_name] = {
                'shift_name': shift_name,
                'start_time': schedule.shift.start_time.strftime('%H:%M'),
                'end_time': schedule.shift.end_time.strftime('%H:%M'),
                'employees': [],
                'employee_count': 0,
                'hours': schedule.shift.total_hours
            }
        
        coverage[date_key]['shifts'][shift_name]['employees'].append({
            'id': schedule.employee.id,
            'name': schedule.employee.get_full_name(),
            'employee_id': schedule.employee.employee_id,
            'status': schedule.status
        })
        coverage[date_key]['shifts'][shift_name]['employee_count'] += 1
        coverage[date_key]['total_employees'] += 1
        coverage[date_key]['total_hours'] += schedule.shift.total_hours
    
    return Response({
        'coverage': list(coverage.values()),
        'period': f"{start_date} to {end_date}",
        'total_days': (end_date - start_date).days + 1
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsManagerOrHR])
def bulk_shift_assignment(request):
    """Bulk assign shifts to multiple employees"""
    shift_id = request.data.get('shift_id')
    employee_ids = request.data.get('employee_ids', [])
    dates = request.data.get('dates', [])  # List of dates
    notes = request.data.get('notes', '')
    
    if not shift_id or not employee_ids or not dates:
        return Response({
            'error': 'shift_id, employee_ids, and dates are required'
        }, status=400)
    
    try:
        shift = Shift.objects.get(id=shift_id)
    except Shift.DoesNotExist:
        return Response({'error': 'Shift not found'}, status=404)
    
    created_schedules = []
    conflicts = []
    
    for date_str in dates:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            continue
        
        for employee_id in employee_ids:
            # Check for conflicts
            existing = ShiftSchedule.objects.filter(
                employee_id=employee_id,
                date=date_obj
            ).exists()
            
            if existing:
                conflicts.append({
                    'employee_id': employee_id,
                    'date': date_str,
                    'reason': 'Employee already has a shift on this date'
                })
                continue
            
            # Create schedule
            try:
                schedule = ShiftSchedule.objects.create(
                    employee_id=employee_id,
                    shift=shift,
                    date=date_obj,
                    notes=notes,
                    created_by=request.user
                )
                created_schedules.append(schedule)
            except Exception as e:
                conflicts.append({
                    'employee_id': employee_id,
                    'date': date_str,
                    'reason': str(e)
                })
    
    return Response({
        'message': f'Created {len(created_schedules)} shift assignments',
        'created_count': len(created_schedules),
        'conflicts': conflicts,
        'schedules': ShiftScheduleSerializer(created_schedules, many=True).data
    })


@login_required
def shifts_schedule_web(request):
    """Web-based shifts schedule view"""
    user = request.user
    
    # Get query parameters
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build queryset
    shifts = ShiftSchedule.objects.filter(employee=user)
    
    if status_filter:
        shifts = shifts.filter(status=status_filter)
    
    if date_from:
        shifts = shifts.filter(date__gte=date_from)
    
    if date_to:
        shifts = shifts.filter(date__lte=date_to)
    
    # Order by date
    shifts = shifts.order_by('date', 'shift__start_time')
    
    # Get upcoming shifts
    today = timezone.now().date()
    upcoming_shifts = shifts.filter(date__gte=today, status='scheduled')[:5]
    
    # Get recent shifts
    recent_shifts = shifts.filter(date__lt=today).order_by('-date')[:5]
    
    context = {
        'shifts': shifts,
        'upcoming_shifts': upcoming_shifts,
        'recent_shifts': recent_shifts,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'shifts/schedule.html', context)


@login_required
def team_schedule_web(request):
    """Web-based team schedule view for managers"""
    user = request.user
    
    # Check if user can manage team schedules
    if not user.can_manage_attendance():
        return render(request, 'shifts/access_denied.html')
    
    # Get query parameters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    employee_filter = request.GET.get('employee')
    
    # Get team members
    from users.models import User
    team_members = User.objects.filter(manager=user)
    
    # Build queryset for team schedules
    queryset = ShiftSchedule.objects.filter(employee__in=team_members)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
        
    if employee_filter:
        queryset = queryset.filter(employee_id=employee_filter)
    
    # Order by date and time
    queryset = queryset.order_by('date', 'shift__start_time').select_related('employee', 'shift')
    
    # Paginate results
    from django.core.paginator import Paginator
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    schedules = paginator.get_page(page_number)
    
    # Get summary statistics
    today = timezone.now().date()
    summary_stats = {
        'total': queryset.count(),
        'today': queryset.filter(date=today).count(),
        'this_week': queryset.filter(date__week=today.isocalendar()[1]).count(),
        'team_size': team_members.count(),
    }
    
    context = {
        'schedules': schedules,
        'team_members': team_members,
        'summary_stats': summary_stats,
        'date_from': date_from,
        'date_to': date_to,
        'employee_filter': employee_filter,
        'today': today,
    }
    
    return render(request, 'shifts/team_schedule.html', context)


@login_required
def create_schedule_web(request):
    """Web-based schedule creation view"""
    user = request.user
    
    # Check if user can manage team schedules
    if not user.can_manage_attendance():
        return render(request, 'shifts/access_denied.html')
    
    # Get team members and shifts
    from users.models import User
    team_members = User.objects.filter(manager=user)
    shifts = Shift.objects.filter(is_active=True)
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        shift_id = request.POST.get('shift')
        date = request.POST.get('date')
        notes = request.POST.get('notes', '')
        
        try:
            employee = User.objects.get(id=employee_id, manager=user)
            shift = Shift.objects.get(id=shift_id, is_active=True)
            
            # Check if schedule already exists
            if ShiftSchedule.objects.filter(employee=employee, date=date).exists():
                messages.error(request, f'{employee.get_full_name()} already has a schedule on {date}.')
            else:
                # Create the schedule
                schedule = ShiftSchedule.objects.create(
                    employee=employee,
                    shift=shift,
                    date=date,
                    notes=notes,
                    created_by=user
                )
                messages.success(request, f'Schedule created successfully for {employee.get_full_name()}.')
                return redirect('shifts:schedule_team')
                
        except User.DoesNotExist:
            messages.error(request, 'Invalid employee selected.')
        except Shift.DoesNotExist:
            messages.error(request, 'Invalid shift selected.')
        except Exception as e:
            messages.error(request, f'Error creating schedule: {str(e)}')
    
    context = {
        'team_members': team_members,
        'shifts': shifts,
        'today': timezone.now().date(),
    }
    
    return render(request, 'shifts/create_schedule.html', context)
