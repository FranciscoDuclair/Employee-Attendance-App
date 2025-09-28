

from django.urls import path
from . import views

app_name = 'shifts'

urlpatterns = [
    # Shift management
    path('shifts/', views.ShiftListView.as_view(), name='shift-list'),
    path('shifts/<int:pk>/', views.ShiftDetailView.as_view(), name='shift-detail'),
    
    # Shift template management
    path('templates/', views.ShiftTemplateListView.as_view(), name='template-list'),
    path('templates/<int:pk>/', views.ShiftTemplateDetailView.as_view(), name='template-detail'),
    path('templates/create-schedules/', views.create_shift_template_schedules, name='template-create-schedules'),
    
    # Shift schedule management
    path('schedules/', views.ShiftScheduleListView.as_view(), name='schedule-list'),
    path('schedules/<int:pk>/', views.ShiftScheduleDetailView.as_view(), name='schedule-detail'),
    
    # Bulk operations
    path('bulk-create/', views.ShiftBulkCreateView.as_view(), name='bulk-create'),
    path('bulk-assignment/', views.bulk_shift_assignment, name='bulk-assignment'),
    path('check-conflicts/', views.ShiftConflictCheckView.as_view(), name='check-conflicts'),
    
    # Reporting and analytics
    path('reports/', views.ShiftReportView.as_view(), name='reports'),
    path('summary/', views.ShiftSummaryView.as_view(), name='summary'),
    path('coverage-report/', views.shift_coverage_report, name='coverage-report'),
    
    # Calendar and visualization
    path('calendar/', views.shift_calendar, name='shift-calendar'),
    
    # Shift actions
    path('schedules/<int:pk>/start/', views.start_shift, name='start-shift'),
    path('schedules/<int:pk>/complete/', views.complete_shift, name='complete-shift'),
    path('schedules/<int:pk>/cancel/', views.cancel_shift, name='cancel-shift'),
    
    # Shift management features
    path('request-swap/', views.request_shift_swap, name='request-swap'),
    
    # Personal shifts
    path('my-shifts/', views.my_shifts, name='my-shifts'),
    
    # Additional URL patterns for template compatibility
    path('schedule/', views.shifts_schedule_web, name='schedule'),
    path('schedule-team/', views.team_schedule_web, name='schedule_team'),
    path('create-schedule/', views.create_schedule_web, name='create_schedule'),
]
