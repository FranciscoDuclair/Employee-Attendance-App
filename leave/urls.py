from django.urls import path
from .views import (
	LeaveTypeListCreateView, LeaveTypeDetailView,
	LeaveRequestCreateView, LeaveRequestListView, LeaveRequestDetailView, LeaveRequestEditView, LeaveApprovalView,
	LeaveBalanceListView, my_leave_requests, allocate_leave_balance, bulk_allocate_leave,
	leave_calendar, leave_statistics, leave_reports, cancel_leave_request, bulk_leave_actions,
	leave_dashboard, team_requests_web, leave_requests_web, leave_calendar_web
)

app_name = 'leave'

urlpatterns = [
	# Leave Dashboard
	path('', leave_dashboard, name='dashboard'),

	# Leave types (HR/Admin)
	path('types/', LeaveTypeListCreateView.as_view(), name='leave_types'),
	path('types/<int:pk>/', LeaveTypeDetailView.as_view(), name='leave_type_detail'),

	# Leave requests
	path('requests/', leave_requests_web, name='request_list'),
	path('requests/create/', LeaveRequestCreateView.as_view(), name='request_create'),
	path('requests/<int:pk>/', LeaveRequestDetailView.as_view(), name='detail'),
	path('requests/<int:pk>/edit/', LeaveRequestEditView.as_view(), name='request_edit'),
	path('requests/<int:pk>/approve/', LeaveApprovalView.as_view(), name='leave_request_approve'),
	path('requests/<int:pk>/cancel/', cancel_leave_request, name='request_cancel'),
	
	# Bulk operations
	path('requests/bulk-actions/', bulk_leave_actions, name='bulk_leave_actions'),

	# Leave balances
	path('balances/', LeaveBalanceListView.as_view(), name='leave_balances'),
	path('balances/allocate/', allocate_leave_balance, name='allocate_leave_balance'),
	path('balances/bulk-allocate/', bulk_allocate_leave, name='bulk_allocate_leave'),

	# User-specific endpoints
	path('my/', my_leave_requests, name='my_leave_requests'),

	# Additional URL patterns for template compatibility
	path('api/team-requests/', team_requests_web, name='team_requests'),
	path('employee/<int:employee_id>/requests/', LeaveRequestListView.as_view(), name='employee_requests'),

	# Reports and analytics
	path('calendar/', leave_calendar_web, name='calendar'),
	path('statistics/', leave_statistics, name='leave_statistics'),
	path('reports/', leave_reports, name='leave_reports'),
]
