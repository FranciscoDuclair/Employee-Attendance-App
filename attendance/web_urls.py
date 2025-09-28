from django.urls import path
from . import web_views

app_name = 'attendance_web'

urlpatterns = [
    # Dashboard - Role-based routing is handled in the view
    path('', web_views.DashboardView.as_view(), name='dashboard'),
    
    # User Profile
    path('profile/', web_views.ProfileView.as_view(), name='profile'),
    
    # Team Management (for managers and admins)
    path('team/attendance/', web_views.TeamAttendanceView.as_view(), name='team_attendance'),
    path('team/performance/', web_views.TeamPerformanceView.as_view(), name='team_performance'),
    
    # Approvals (for managers and admins)
    path('approvals/', web_views.PendingApprovalsView.as_view(), name='pending_approvals'),
    path('approve/<int:request_id>/<str:action>/', web_views.ProcessApprovalView.as_view(), 
         name='process_approval'),
    path('request/<int:request_id>/', web_views.ViewRequestView.as_view(), name='view_request'),
    
    # Face Recognition Management
    path('face-setup/', web_views.FaceSetupView.as_view(), name='face_setup'),
    path('face-capture/', web_views.FaceCaptureView.as_view(), name='face_capture'),
    path('face-status/', web_views.FaceStatusView.as_view(), name='face_status'),
    
    # Attendance Management
    path('attendance/', web_views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/checkin/', web_views.CheckInView.as_view(), name='checkin'),
    path('attendance/checkout/', web_views.CheckOutView.as_view(), name='checkout'),
    
    # Reports
    path('reports/', web_views.ReportsView.as_view(), name='reports'),
    path('reports/export/', web_views.ExportReportView.as_view(), name='export_report'),
    
    # Settings
    path('settings/', web_views.SettingsView.as_view(), name='settings'),
    path('system-settings/', web_views.SystemSettingsView.as_view(), name='system_settings'),
    
    # User Management (admin only)
    path('users/', web_views.UserListView.as_view(), name='user_list'),
    path('users/add/', web_views.UserCreateView.as_view(), name='add_user'),
    path('users/<int:pk>/', web_views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/edit/', web_views.UserUpdateView.as_view(), name='edit_user'),
    path('users/<int:user_id>/delete/', web_views.UserDeleteView.as_view(), name='delete_user'),
    
    # Authentication
    path('login/', web_views.LoginView.as_view(), name='login'),
    path('logout/', web_views.LogoutView.as_view(), name='logout'),
    path('change-password/', web_views.ChangePasswordView.as_view(), name='change_password'),
    
    # Activity Logs (admin only)
    path('activity-logs/', web_views.ActivityLogView.as_view(), name='activity_logs'),
    
    # Additional URL patterns for template compatibility
    path('bulk-actions/', web_views.BulkActionsView.as_view(), name='bulk_actions'),
    path('employee-attendance/<int:user_id>/', web_views.EmployeeAttendanceView.as_view(), name='employee_attendance'),
    path('employee-detail/<int:pk>/', web_views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('team-status-api/', web_views.TeamStatusAPIView.as_view(), name='team_status_api'),
    path('export-attendance/', web_views.ExportReportView.as_view(), name='export_attendance'),
    path('send-reminder/', web_views.DashboardView.as_view(), name='send_reminder'),
    path('remove-profile-picture/', web_views.ProfileView.as_view(), name='remove_profile_picture'),
    path('upload-profile-picture/', web_views.ProfileView.as_view(), name='upload_profile_picture'),
    path('face-recognition-verify/', web_views.FaceCaptureView.as_view(), name='face_recognition_verify'),
    path('manual-attendance/', web_views.CheckInView.as_view(), name='manual_attendance'),
    path('audit-logs/', web_views.ActivityLogView.as_view(), name='audit_logs'),
    
    # Missing URL patterns that were causing template errors
    path('today-attendance/', web_views.AttendanceListView.as_view(), name='today_attendance'),
    path('attendance-timeline/', web_views.ReportsView.as_view(), name='attendance_timeline'),
    path('approve-request/<int:approval_id>/<str:action>/', web_views.ProcessApprovalView.as_view(), name='approve_request'),
    path('view-request/<int:request_id>/', web_views.ViewRequestView.as_view(), name='view_request'),
    path('team-attendance/', web_views.AttendanceListView.as_view(), name='team_attendance'),
    path('system-health/', web_views.SystemHealthView.as_view(), name='system_health'),
    path('system-settings/', web_views.SystemSettingsView.as_view(), name='system_settings'),
    path('user-list/', web_views.UserListView.as_view(), name='user_list'),
    path('reports/', web_views.ReportsView.as_view(), name='reports'),
]
