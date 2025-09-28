from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PayrollListView, PayrollDetailView, PayrollCreateView, PayrollCalculationView,
    PayrollReportView, PayrollSummaryView, PayrollBulkActionView, PayrollAdjustmentView,
    PayrollComparisonView, my_payroll, auto_generate_payroll, payroll_web_view, payslip_download_web,
    generate_payslips_web
)

app_name = 'payroll'

# Create router for ViewSets
router = DefaultRouter()

urlpatterns = [
    # Basic payroll management
    path('list/', PayrollListView.as_view(), name='payroll_list'),
    path('create/', PayrollCreateView.as_view(), name='payroll_create'),
    path('<int:pk>/', PayrollDetailView.as_view(), name='payroll_detail'),
    
    # Payroll calculations
    path('calculate/', PayrollCalculationView.as_view(), name='payroll_calculate'),
    path('auto-generate/', auto_generate_payroll, name='auto_generate_payroll'),
    
    # Reports and analytics
    path('reports/', PayrollReportView.as_view(), name='payroll_reports'),
    path('summary/', PayrollSummaryView.as_view(), name='payroll_summary'),
    
    # Bulk operations
    path('bulk-actions/', PayrollBulkActionView.as_view(), name='payroll_bulk_actions'),
    
    # Adjustments and comparisons
    path('compare/', PayrollComparisonView.as_view(), name='payroll_comparison'),
    
    # Employee access
    path('my-payroll/', my_payroll, name='my_payroll'),
    
    # Web views
    path('my-payroll/', my_payroll, name='my_payroll'),
    path('payroll-web/', payroll_web_view, name='payroll_web'),
    path('payslip-download/<int:payroll_id>/', payslip_download_web, name='payslip_download'),
    path('generate-payslips/', generate_payslips_web, name='generate_payslips'),
    path('my-payroll-web/', payroll_web_view, name='my_payroll_web'),
]
