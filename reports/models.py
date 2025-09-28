from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ReportTemplate(models.Model):
    """
    Model to store report templates for different types of reports
    """
    REPORT_TYPES = [
        ('attendance', 'Attendance Report'),
        ('leave', 'Leave Report'),
        ('payroll', 'Payroll Report'),
        ('shift', 'Shift Report'),
        ('employee', 'Employee Report'),
        ('department', 'Department Report'),
        ('custom', 'Custom Report'),
    ]
    
    FORMAT_TYPES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    format_type = models.CharField(max_length=10, choices=FORMAT_TYPES, default='pdf')
    
    # Template configuration
    fields = models.JSONField(
        default=list,
        help_text="List of fields to include in the report"
    )
    filters = models.JSONField(
        default=dict,
        help_text="Default filters for the report"
    )
    grouping = models.JSONField(
        default=dict,
        help_text="Grouping configuration"
    )
    sorting = models.JSONField(
        default=dict,
        help_text="Sorting configuration"
    )
    
    # Access control
    is_public = models.BooleanField(default=False)
    allowed_roles = models.JSONField(
        default=list,
        help_text="Roles allowed to access this report"
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'reports_templates'
        ordering = ['name']
        indexes = [
            models.Index(fields=['report_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportExecution(models.Model):
    """
    Model to track report executions and store generated reports
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=ReportTemplate.REPORT_TYPES)
    format_type = models.CharField(max_length=10, choices=ReportTemplate.FORMAT_TYPES)
    
    # Execution parameters
    parameters = models.JSONField(
        default=dict,
        help_text="Parameters used to generate the report"
    )
    filters = models.JSONField(
        default=dict,
        help_text="Filters applied to the report"
    )
    
    # Execution details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # File storage
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    record_count = models.PositiveIntegerField(null=True, blank=True)
    generation_time = models.DurationField(null=True, blank=True)
    
    # Access control
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_reports')
    is_public = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reports_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requested_by']),
            models.Index(fields=['report_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    @property
    def is_expired(self):
        """Check if the report has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def mark_as_downloaded(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class Dashboard(models.Model):
    """
    Model to store custom dashboard configurations
    """
    DASHBOARD_TYPES = [
        ('employee', 'Employee Dashboard'),
        ('manager', 'Manager Dashboard'),
        ('hr', 'HR Dashboard'),
        ('executive', 'Executive Dashboard'),
        ('custom', 'Custom Dashboard'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    dashboard_type = models.CharField(max_length=20, choices=DASHBOARD_TYPES)
    
    # Dashboard configuration
    widgets = models.JSONField(
        default=list,
        help_text="List of widgets and their configurations"
    )
    layout = models.JSONField(
        default=dict,
        help_text="Dashboard layout configuration"
    )
    refresh_interval = models.PositiveIntegerField(
        default=300,
        help_text="Auto-refresh interval in seconds"
    )
    
    # Access control
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    allowed_roles = models.JSONField(
        default=list,
        help_text="Roles allowed to access this dashboard"
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_dashboards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'reports_dashboards'
        ordering = ['name']
        indexes = [
            models.Index(fields=['dashboard_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_dashboard_type_display()})"


class AnalyticsMetric(models.Model):
    """
    Model to store analytics metrics and KPIs
    """
    METRIC_TYPES = [
        ('attendance_rate', 'Attendance Rate'),
        ('late_arrival_rate', 'Late Arrival Rate'),
        ('leave_utilization', 'Leave Utilization'),
        ('overtime_hours', 'Overtime Hours'),
        ('productivity_score', 'Productivity Score'),
        ('shift_coverage', 'Shift Coverage'),
        ('payroll_cost', 'Payroll Cost'),
        ('employee_satisfaction', 'Employee Satisfaction'),
        ('custom', 'Custom Metric'),
    ]
    
    name = models.CharField(max_length=200)
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    description = models.TextField(blank=True)
    
    # Metric calculation
    calculation_method = models.TextField(
        help_text="Description or formula for calculating this metric"
    )
    query = models.TextField(
        blank=True,
        help_text="SQL query or calculation logic"
    )
    
    # Metric value
    current_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    previous_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Metric metadata
    unit = models.CharField(max_length=20, blank=True, help_text="Unit of measurement")
    data_source = models.CharField(max_length=100, blank=True)
    update_frequency = models.CharField(
        max_length=20,
        choices=[
            ('real_time', 'Real Time'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='daily'
    )
    
    last_calculated = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'reports_analytics_metrics'
        ordering = ['name']
        indexes = [
            models.Index(fields=['metric_type']),
            models.Index(fields=['last_calculated']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.current_value} {self.unit})"
    
    @property
    def trend(self):
        """Calculate trend compared to previous value"""
        if self.current_value is not None and self.previous_value is not None:
            if self.current_value > self.previous_value:
                return 'up'
            elif self.current_value < self.previous_value:
                return 'down'
        return 'stable'
    
    @property
    def target_achievement(self):
        """Calculate percentage of target achievement"""
        if self.current_value is not None and self.target_value is not None and self.target_value != 0:
            return (self.current_value / self.target_value) * 100
        return None
