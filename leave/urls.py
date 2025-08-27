from django.urls import path
from .views import (
	LeaveTypeListCreateView, LeaveTypeDetailView,
	LeaveRequestCreateView, LeaveRequestListView, LeaveRequestDetailView, LeaveApprovalView,
	LeaveBalanceListView, my_leave_requests, allocate_leave_balance
)

urlpatterns = [
	# Leave types (HR/Admin)
	path('types/', LeaveTypeListCreateView.as_view(), name='leave_types'),
	path('types/<int:pk>/', LeaveTypeDetailView.as_view(), name='leave_type_detail'),

	# Leave requests
	path('requests/', LeaveRequestListView.as_view(), name='leave_requests'),
	path('requests/create/', LeaveRequestCreateView.as_view(), name='leave_request_create'),
	path('requests/<int:pk>/', LeaveRequestDetailView.as_view(), name='leave_request_detail'),
	path('requests/<int:pk>/approve/', LeaveApprovalView.as_view(), name='leave_request_approve'),

	# Balances and self endpoints
	path('balances/', LeaveBalanceListView.as_view(), name='leave_balances'),
	path('my/', my_leave_requests, name='my_leave_requests'),
	path('balances/allocate/', allocate_leave_balance, name='allocate_leave_balance'),
]
