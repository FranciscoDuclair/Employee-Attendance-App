from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PayrollListView, PayrollDetailView, PayrollCreateView, PayrollCalculationView,
    PayrollReportView, PayrollSummaryView, PayrollBulkActionView, PayrollAdjustmentView,
    PayrollComparisonView, my_payroll, auto_generate_payroll
)

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
    path('adjustments/', PayrollAdjustmentView.as_view(), name='payroll_adjustments'),
    path('compare/', PayrollComparisonView.as_view(), name='payroll_comparison'),
    
    # Employee access
    path('my-payroll/', my_payroll, name='my_payroll'),
    
    # Include router URLs
    path('', include(router.urls)),
]
