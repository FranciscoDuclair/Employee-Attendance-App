from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'reports'

# Create router for ViewSets
router = DefaultRouter()

urlpatterns = [
    # Report Templates
    path('templates/', views.ReportTemplateListView.as_view(), name='report-template-list'),
    path('templates/<int:pk>/', views.ReportTemplateDetailView.as_view(), name='report-template-detail'),
    
    # Report Executions
    path('executions/', views.ReportExecutionListView.as_view(), name='report-execution-list'),
    path('executions/<int:pk>/', views.ReportExecutionDetailView.as_view(), name='report-execution-detail'),
    path('executions/<int:execution_id>/download/', views.download_report, name='download-report'),
    
    # Quick Report Generation
    path('generate/attendance/', views.generate_attendance_report, name='generate-attendance-report'),
    path('generate/leave/', views.generate_leave_report, name='generate-leave-report'),
    
    # Dashboard Management
    path('dashboards/', views.DashboardListView.as_view(), name='dashboard-list'),
    path('dashboards/<int:dashboard_id>/data/', views.dashboard_data, name='dashboard-data'),
    
    # Analytics & Metrics
    path('metrics/', views.AnalyticsMetricListView.as_view(), name='analytics-metric-list'),
    path('analytics/', views.analytics_data, name='analytics-data'),
    path('analytics/attendance/', views.attendance_analytics, name='attendance-analytics'),
    
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional URL patterns for template compatibility
    path('team-report/', views.generate_team_report_web, name='team_report'),
    path('team-analytics/', views.team_analytics_web, name='team_analytics'),
]
