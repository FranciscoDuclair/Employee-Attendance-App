from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Q, Sum

from .models import LeaveRequest, LeaveType, LeaveBalance
from users.models import User


class LeaveDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for leave management"""
    template_name = 'leave/leave_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()
        
        # Get user's leave balances
        leave_balances = LeaveBalance.objects.filter(
            user=user,
            year=today.year
        ).select_related('leave_type')
        
        # Get pending leave requests
        pending_requests = LeaveRequest.objects.filter(
            user=user,
            status='pending'
        ).order_by('start_date')
        
        # Get upcoming approved leaves
        upcoming_leaves = LeaveRequest.objects.filter(
            user=user,
            status='approved',
            start_date__gte=today
        ).order_by('start_date')[:5]
        
        # Get leave statistics for the year
        leave_stats = LeaveRequest.objects.filter(
            user=user,
            start_date__year=today.year
        ).values('leave_type__name').annotate(
            total_days=Sum('total_days')
        )
        
        context.update({
            'leave_balances': leave_balances,
            'pending_requests': pending_requests,
            'upcoming_leaves': upcoming_leaves,
            'leave_stats': leave_stats,
            'current_year': today.year,
        })
        
        # Add manager-specific data
        if hasattr(user, 'is_manager') and user.is_manager:
            team_pending = LeaveRequest.objects.filter(
                user__manager=user,
                status='pending'
            ).select_related('user', 'leave_type').order_by('start_date')
            
            team_on_leave = LeaveRequest.objects.filter(
                user__manager=user,
                status='approved',
                start_date__lte=today,
                end_date__gte=today
            ).select_related('user', 'leave_type')
            
            context.update({
                'team_pending': team_pending,
                'team_on_leave': team_on_leave,
                'team_members_count': User.objects.filter(manager=user).count(),
            })
            
        # Add admin-specific data
        if user.is_staff:
            all_pending = LeaveRequest.objects.filter(
                status='pending'
            ).select_related('user', 'leave_type').order_by('start_date')
            
            context['all_pending'] = all_pending
            
        return context


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new leave request"""
    model = LeaveRequest
    fields = ['leave_type', 'start_date', 'end_date', 'reason', 'emergency_contact', 'emergency_phone']
    template_name = 'leave/leave_request_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter active leave types
        form.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        
        # Add date picker attributes
        form.fields['start_date'].widget.attrs.update({'class': 'datepicker'})
        form.fields['end_date'].widget.attrs.update({'class': 'datepicker'})
        
        # Add emergency contact info as optional
        form.fields['emergency_contact'].required = False
        form.fields['emergency_phone'].required = False
        
        return form
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Calculate total days
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        form.instance.total_days = self.calculate_working_days(start_date, end_date)
        
        # Set status based on leave type requirements
        leave_type = form.cleaned_data['leave_type']
        if not leave_type.requires_approval:
            form.instance.status = 'approved'
            form.instance.approved_by = self.request.user
            form.instance.approved_at = timezone.now()
        
        response = super().form_valid(form)
        messages.success(self.request, 'Leave request submitted successfully.')
        
        # If auto-approved, update leave balance
        if form.instance.status == 'approved':
            form.instance.update_leave_balance()
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('leave:dashboard')
    
    def calculate_working_days(self, start_date, end_date):
        """Calculate working days between two dates (excludes weekends)"""
        if start_date > end_date:
            return 0
            
        # Calculate the difference in days
        delta = end_date - start_date
        total_days = delta.days + 1  # Include both start and end dates
        
        # Calculate weekend days in the range
        weekends = 0
        current = start_date
        for _ in range(total_days):
            if current.weekday() >= 5:  # Saturday=5, Sunday=6
                weekends += 1
            current += timedelta(days=1)
        
        return total_days - weekends


class LeaveRequestDetailView(LoginRequiredMixin, DetailView):
    """View for viewing leave request details"""
    model = LeaveRequest
    template_name = 'leave/leave_request_detail.html'
    context_object_name = 'leave_request'
    
    def get_queryset(self):
        # Users can only see their own leave requests unless they are managers/admins
        qs = super().get_queryset()
        if not (self.request.user.is_staff or hasattr(self.request.user, 'is_manager') and self.request.user.is_manager):
            qs = qs.filter(user=self.request.user)
        return qs


class LeaveRequestUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for updating a leave request (only for pending requests)"""
    model = LeaveRequest
    fields = ['leave_type', 'start_date', 'end_date', 'reason', 'emergency_contact', 'emergency_phone']
    template_name = 'leave/leave_request_form.html'
    
    def test_func(self):
        leave_request = self.get_object()
        # Only allow updates if the request is pending and user is the owner
        return (leave_request.user == self.request.user and 
                leave_request.status == 'pending')
    
    def get_success_url(self):
        return reverse_lazy('leave:detail', kwargs={'pk': self.object.pk})


class LeaveRequestCancelView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for cancelling a leave request"""
    model = LeaveRequest
    fields = []
    template_name = 'leave/leave_cancel_confirm.html'
    
    def test_func(self):
        leave_request = self.get_object()
        # Only allow cancellation if the request is pending or approved and not in the past
        return (leave_request.user == self.request.user and 
                leave_request.status in ['pending', 'approved'] and
                leave_request.start_date >= date.today())
    
    def form_valid(self, form):
        form.instance.status = 'cancelled'
        response = super().form_valid(form)
        messages.success(self.request, 'Leave request has been cancelled.')
        return response
    
    def get_success_url(self):
        return reverse_lazy('leave:dashboard')


class LeaveRequestApproveRejectView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for managers/admins to approve or reject leave requests"""
    model = LeaveRequest
    fields = ['approval_notes']
    template_name = 'leave/leave_review.html'
    
    def test_func(self):
        # Only managers and admins can approve/reject
        if not (self.request.user.is_staff or hasattr(self.request.user, 'is_manager') and self.request.user.is_manager):
            return False
            
        # Check if the user is the manager of the employee who requested leave
        leave_request = self.get_object()
        return (leave_request.user.manager == self.request.user or 
                self.request.user.is_staff)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = self.kwargs.get('action', 'review')
        return context
    
    def form_valid(self, form):
        action = self.kwargs.get('action')
        
        if action == 'approve':
            form.instance.status = 'approved'
            form.instance.approved_by = self.request.user
            form.instance.approved_at = timezone.now()
            success_message = 'Leave request has been approved.'
            
            # Update leave balance
            form.instance.update_leave_balance()
            
        elif action == 'reject':
            form.instance.status = 'rejected'
            success_message = 'Leave request has been rejected.'
        else:
            return self.form_invalid(form)
        
        response = super().form_valid(form)
        messages.success(self.request, success_message)
        
        # TODO: Send notification to employee
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('leave:team_requests')


class TeamLeaveRequestsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View for managers to see their team's leave requests"""
    model = LeaveRequest
    template_name = 'leave/team_requests.html'
    context_object_name = 'leave_requests'
    paginate_by = 10
    
    def test_func(self):
        # Only managers and admins can view team requests
        return (self.request.user.is_staff or 
                hasattr(self.request.user, 'is_manager') and self.request.user.is_manager)
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status in ['pending', 'approved', 'rejected', 'cancelled']:
            qs = qs.filter(status=status)
        
        # Filter by date range if provided
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            qs = qs.filter(start_date__gte=start_date)
        if end_date:
            qs = qs.filter(end_date__lte=end_date)
        
        # For managers, only show their team's requests
        if not self.request.user.is_staff:
            qs = qs.filter(user__manager=self.request.user)
        
        return qs.select_related('user', 'leave_type', 'approved_by').order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter values to context
        context['status_filter'] = self.request.GET.get('status', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
        
        # Add summary statistics
        if not self.request.user.is_staff:
            team_members = User.objects.filter(manager=self.request.user)
            context['team_members_count'] = team_members.count()
            
            # Get leave balances for the team
            current_year = date.today().year
            leave_balances = LeaveBalance.objects.filter(
                user__in=team_members,
                year=current_year
            ).values('leave_type__name').annotate(
                total_allocated=Sum('total_allocated'),
                used_days=Sum('used_days')
            )
            
            context['leave_balances'] = leave_balances
        
        return context


class LeaveCalendarView(LoginRequiredMixin, TemplateView):
    """View for displaying a calendar of leave requests"""
    template_name = 'leave/leave_calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get the year and month from URL parameters or use current
        year = int(self.kwargs.get('year', date.today().year))
        month = int(self.kwargs.get('month', date.today().month))
        
        # Calculate previous and next month for navigation
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        # Get the first day of the month and the first day to show on the calendar
        first_day = date(year, month, 1)
        first_day_weekday = first_day.weekday()  # Monday is 0, Sunday is 6
        
        # Calculate the first day to show (previous month)
        if first_day_weekday > 0:  # If not Monday
            prev_days = first_day_weekday
            prev_month_days = (first_day - timedelta(days=prev_days)).day
            calendar_start = date(year, month, 1) - timedelta(days=prev_days)
        else:
            calendar_start = first_day
        
        # Calculate the last day of the month and the last day to show on the calendar
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        
        last_day = next_month_first - timedelta(days=1)
        last_day_weekday = last_day.weekday()
        
        # Calculate the last day to show (next month)
        if last_day_weekday < 6:  # If not Sunday
            next_days = 6 - last_day_weekday
            calendar_end = last_day + timedelta(days=next_days)
        else:
            calendar_end = last_day
        
        # Generate the calendar days
        calendar_days = []
        current_day = calendar_start
        
        while current_day <= calendar_end:
            calendar_days.append(current_day)
            current_day += timedelta(days=1)
        
        # Get leave requests for the visible period
        if user.is_staff or hasattr(user, 'is_manager') and user.is_manager:
            # For managers/admins, show team's leaves
            leave_requests = LeaveRequest.objects.filter(
                Q(user__manager=user) | Q(user=user) if not user.is_staff else Q(),
                start_date__lte=calendar_end,
                end_date__gte=calendar_start,
                status='approved'
            ).select_related('user', 'leave_type')
        else:
            # For regular users, only show their own leaves
            leave_requests = LeaveRequest.objects.filter(
                user=user,
                start_date__lte=calendar_end,
                end_date__gte=calendar_start,
                status='approved'
            ).select_related('leave_type')
        
        # Create a dictionary of leave requests by date
        leaves_by_date = {}
        for leave in leave_requests:
            current_date = max(leave.start_date, calendar_start)
            end_date = min(leave.end_date, calendar_end)
            
            while current_date <= end_date:
                if current_date not in leaves_by_date:
                    leaves_by_date[current_date] = []
                leaves_by_date[current_date].append(leave)
                current_date += timedelta(days=1)
        
        context.update({
            'year': year,
            'month': month,
            'month_name': first_day.strftime('%B'),
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
            'calendar_days': calendar_days,
            'leaves_by_date': leaves_by_date,
            'weekdays': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'today': date.today(),
        })
        
        return context
