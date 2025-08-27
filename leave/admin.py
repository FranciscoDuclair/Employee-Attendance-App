from django.contrib import admin
from .models import LeaveType, LeaveRequest, LeaveBalance


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
	list_display = ['name', 'max_days_per_year', 'requires_approval', 'is_paid', 'is_active']
	search_fields = ['name', 'description']
	list_filter = ['requires_approval', 'is_paid', 'is_active']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
	list_display = ['user', 'leave_type', 'start_date', 'end_date', 'total_days', 'status', 'approved_by', 'created_at']
	list_filter = ['leave_type', 'status', 'start_date', 'end_date', 'created_at']
	search_fields = ['user__first_name', 'user__last_name', 'user__employee_id']
	ordering = ['-created_at']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
	list_display = ['user', 'leave_type', 'year', 'total_allocated', 'used_days', 'remaining_days']
	list_filter = ['year', 'leave_type']
	search_fields = ['user__first_name', 'user__last_name', 'user__employee_id']
