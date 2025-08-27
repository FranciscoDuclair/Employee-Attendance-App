from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Avg, Count
from .models import Payroll
from django.utils import timezone


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    """Admin interface for Payroll model"""
    
    list_display = [
        'user', 'month_year', 'basic_salary', 'total_hours_worked',
        'gross_pay', 'net_pay', 'status', 'approved_by', 'created_at'
    ]
    
    list_filter = [
        'month', 'year', 'status', 'user__department', 'user__role',
        'approved_by', 'created_at'
    ]
    
    search_fields = [
        'user__first_name', 'user__last_name', 'user__employee_id',
        'user__email'
    ]
    
    ordering = ['-year', '-month', '-created_at']
    
    readonly_fields = [
        'total_hours_worked', 'regular_hours', 'overtime_hours',
        'regular_pay', 'overtime_pay', 'gross_pay', 'net_pay',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Employee Information', {
            'fields': ('user', 'month', 'year')
        }),
        ('Salary Details', {
            'fields': ('basic_salary', 'hourly_rate')
        }),
        ('Hours & Pay Calculation', {
            'fields': (
                'total_hours_worked', 'regular_hours', 'overtime_hours',
                'regular_pay', 'overtime_pay', 'gross_pay'
            ),
            'classes': ('collapse',)
        }),
        ('Deductions & Net Pay', {
            'fields': ('tax_deduction', 'other_deductions', 'net_pay')
        }),
        ('Approval & Status', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def month_year(self, obj):
        """Display month/year in a readable format"""
        month_names = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        return f"{month_names[obj.month]} {obj.year}"
    month_year.short_description = 'Period'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'approved_by')
    
    # Admin actions
    actions = [
        'approve_payroll', 'reject_payroll', 'recalculate_payroll',
        'export_to_csv', 'generate_summary_report'
    ]
    
    def approve_payroll(self, request, queryset):
        """Approve selected payroll records"""
        updated = queryset.update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request, 
            f'{updated} payroll records approved successfully.'
        )
    approve_payroll.short_description = "Approve selected payroll records"
    
    def reject_payroll(self, request, queryset):
        """Reject selected payroll records"""
        updated = queryset.update(status='rejected')
        self.message_user(
            request, 
            f'{updated} payroll records rejected successfully.'
        )
    reject_payroll.short_description = "Reject selected payroll records"
    
    def recalculate_payroll(self, request, queryset):
        """Recalculate selected payroll records"""
        updated = 0
        for payroll in queryset:
            try:
                # Import the calculation method
                from .views import PayrollCalculationView
                view = PayrollCalculationView()
                view.calculate_payroll(payroll)
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f'Error recalculating payroll {payroll.id}: {str(e)}',
                    level='ERROR'
                )
        
        self.message_user(
            request, 
            f'{updated} payroll records recalculated successfully.'
        )
    recalculate_payroll.short_description = "Recalculate selected payroll records"
    
    def export_to_csv(self, request, queryset):
        """Export selected payroll records to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payroll_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Name', 'Department', 'Month', 'Year',
            'Basic Salary', 'Hourly Rate', 'Total Hours', 'Regular Hours',
            'Overtime Hours', 'Regular Pay', 'Overtime Pay', 'Gross Pay',
            'Tax Deduction', 'Other Deductions', 'Net Pay', 'Status'
        ])
        
        for payroll in queryset:
            writer.writerow([
                payroll.user.employee_id,
                payroll.user.get_full_name(),
                payroll.user.department,
                payroll.month,
                payroll.year,
                payroll.basic_salary,
                payroll.hourly_rate,
                payroll.total_hours_worked,
                payroll.regular_hours,
                payroll.overtime_hours,
                payroll.regular_pay,
                payroll.overtime_pay,
                payroll.gross_pay,
                payroll.tax_deduction,
                payroll.other_deductions,
                payroll.net_pay,
                payroll.status
            ])
        
        return response
    export_to_csv.short_description = "Export selected payroll records to CSV"
    
    def generate_summary_report(self, request, queryset):
        """Generate summary report for selected payroll records"""
        total_records = queryset.count()
        total_payroll = queryset.aggregate(total=Sum('net_pay'))['total'] or 0
        total_gross = queryset.aggregate(total=Sum('gross_pay'))['total'] or 0
        total_overtime = queryset.aggregate(total=Sum('overtime_pay'))['total'] or 0
        avg_salary = queryset.aggregate(avg=Avg('net_pay'))['avg'] or 0
        
        # Department breakdown
        dept_breakdown = queryset.values('user__department').annotate(
            count=Count('id'),
            total=Sum('net_pay')
        ).order_by('-total')
        
        # Status breakdown
        status_breakdown = queryset.values('status').annotate(
            count=Count('id'),
            total=Sum('net_pay')
        ).order_by('-total')
        
        report = f"""
        Payroll Summary Report
        
        Total Records: {total_records}
        Total Payroll Amount: ${total_payroll:,.2f}
        Total Gross Pay: ${total_gross:,.2f}
        Total Overtime Pay: ${total_overtime:,.2f}
        Average Salary: ${avg_salary:,.2f}
        
        Department Breakdown:
        """
        
        for dept in dept_breakdown:
            report += f"\n{dept['user__department']}: {dept['count']} employees, ${dept['total']:,.2f}"
        
        report += "\n\nStatus Breakdown:"
        for status in status_breakdown:
            report += f"\n{status['status']}: {status['count']} records, ${status['total']:,.2f}"
        
        self.message_user(request, report)
    generate_summary_report.short_description = "Generate summary report for selected records"
    
    # Custom admin methods
    def get_list_display(self, request):
        """Customize list display based on user permissions"""
        if request.user.is_superuser:
            return self.list_display
        else:
            # Remove sensitive fields for non-superusers
            return [field for field in self.list_display if field != 'approved_by']
    
    def has_add_permission(self, request):
        """Only HR/Admin users can add payroll records"""
        return request.user.is_superuser or hasattr(request.user, 'can_manage_attendance')
    
    def has_change_permission(self, request, obj=None):
        """Only HR/Admin users can change payroll records"""
        return request.user.is_superuser or hasattr(request.user, 'can_manage_attendance')
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete payroll records"""
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        """All authenticated users can view payroll records"""
        return request.user.is_authenticated


# Custom admin site configuration
admin.site.site_header = "Employee Attendance Platform Admin"
admin.site.site_title = "Attendance Platform Admin"
admin.site.index_title = "Welcome to Employee Attendance Platform Administration"
