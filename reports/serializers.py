from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ReportTemplate, ReportExecution, Dashboard, AnalyticsMetric

User = get_user_model()


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ReportTemplate model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    format_type_display = serializers.CharField(source='get_format_type_display', read_only=True)
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type', 'report_type_display',
            'format_type', 'format_type_display', 'fields', 'filters', 'grouping',
            'sorting', 'is_public', 'allowed_roles', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ReportTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating report templates"""
    
    class Meta:
        model = ReportTemplate
        fields = [
            'name', 'description', 'report_type', 'format_type', 'fields',
            'filters', 'grouping', 'sorting', 'is_public', 'allowed_roles'
        ]
    
    def validate_fields(self, value):
        """Validate fields configuration"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Fields must be a list")
        return value
    
    def validate_filters(self, value):
        """Validate filters configuration"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filters must be a dictionary")
        return value


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Serializer for ReportExecution model"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    format_type_display = serializers.CharField(source='get_format_type_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ReportExecution
        fields = [
            'id', 'template', 'template_name', 'name', 'report_type', 'report_type_display',
            'format_type', 'format_type_display', 'parameters', 'filters', 'status',
            'status_display', 'started_at', 'completed_at', 'error_message', 'file_path',
            'file_size', 'download_count', 'record_count', 'generation_time',
            'requested_by', 'requested_by_name', 'is_public', 'expires_at',
            'created_at', 'updated_at', 'is_expired'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'completed_at', 'error_message',
            'file_path', 'file_size', 'download_count', 'record_count',
            'generation_time', 'requested_by', 'created_at', 'updated_at'
        ]


class ReportExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating report executions"""
    
    class Meta:
        model = ReportExecution
        fields = [
            'template', 'name', 'report_type', 'format_type', 'parameters',
            'filters', 'is_public', 'expires_at'
        ]
    
    def validate_template(self, value):
        """Validate template exists and is active"""
        if value and not value.is_active:
            raise serializers.ValidationError("Cannot use inactive template")
        return value


class DashboardSerializer(serializers.ModelSerializer):
    """Serializer for Dashboard model"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    dashboard_type_display = serializers.CharField(source='get_dashboard_type_display', read_only=True)
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'dashboard_type', 'dashboard_type_display',
            'widgets', 'layout', 'refresh_interval', 'is_default', 'is_public',
            'allowed_roles', 'created_by', 'created_by_name', 'created_at',
            'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class DashboardCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating dashboards"""
    
    class Meta:
        model = Dashboard
        fields = [
            'name', 'description', 'dashboard_type', 'widgets', 'layout',
            'refresh_interval', 'is_default', 'is_public', 'allowed_roles'
        ]
    
    def validate_widgets(self, value):
        """Validate widgets configuration"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Widgets must be a list")
        return value
    
    def validate_layout(self, value):
        """Validate layout configuration"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Layout must be a dictionary")
        return value


class AnalyticsMetricSerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsMetric model"""
    metric_type_display = serializers.CharField(source='get_metric_type_display', read_only=True)
    trend = serializers.CharField(read_only=True)
    target_achievement = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = AnalyticsMetric
        fields = [
            'id', 'name', 'metric_type', 'metric_type_display', 'description',
            'calculation_method', 'query', 'current_value', 'previous_value',
            'target_value', 'unit', 'data_source', 'update_frequency',
            'last_calculated', 'created_at', 'updated_at', 'is_active',
            'trend', 'target_achievement'
        ]
        read_only_fields = [
            'id', 'last_calculated', 'created_at', 'updated_at', 'trend', 'target_achievement'
        ]


class AttendanceReportSerializer(serializers.Serializer):
    """Serializer for attendance report parameters"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    department = serializers.CharField(required=False, allow_blank=True)
    employee = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=[('present', 'Present'), ('absent', 'Absent'), ('late', 'Late')],
        required=False,
        allow_blank=True
    )
    format = serializers.ChoiceField(
        choices=[('pdf', 'PDF'), ('csv', 'CSV'), ('json', 'JSON')],
        default='pdf'
    )
    
    def validate(self, data):
        """Validate date range"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        return data


class LeaveReportSerializer(serializers.Serializer):
    """Serializer for leave report parameters"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    department = serializers.CharField(required=False, allow_blank=True)
    employee = serializers.IntegerField(required=False, allow_null=True)
    leave_type = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        required=False,
        allow_blank=True
    )
    format = serializers.ChoiceField(
        choices=[('pdf', 'PDF'), ('csv', 'CSV'), ('json', 'JSON')],
        default='pdf'
    )


class PayrollReportSerializer(serializers.Serializer):
    """Serializer for payroll report parameters"""
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2020, max_value=2030)
    department = serializers.CharField(required=False, allow_blank=True)
    employee = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=[('draft', 'Draft'), ('approved', 'Approved'), ('paid', 'Paid')],
        required=False,
        allow_blank=True
    )
    format = serializers.ChoiceField(
        choices=[('pdf', 'PDF'), ('csv', 'CSV'), ('json', 'JSON')],
        default='pdf'
    )


class ShiftReportSerializer(serializers.Serializer):
    """Serializer for shift report parameters"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    department = serializers.CharField(required=False, allow_blank=True)
    employee = serializers.IntegerField(required=False, allow_null=True)
    shift = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        required=False,
        allow_blank=True
    )
    format = serializers.ChoiceField(
        choices=[('pdf', 'PDF'), ('csv', 'CSV'), ('json', 'JSON')],
        default='pdf'
    )


class DashboardDataSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    widget_type = serializers.CharField()
    title = serializers.CharField()
    data = serializers.JSONField()
    config = serializers.JSONField(required=False)


class AnalyticsDataSerializer(serializers.Serializer):
    """Serializer for analytics data"""
    period = serializers.ChoiceField(
        choices=[('day', 'Daily'), ('week', 'Weekly'), ('month', 'Monthly'), ('year', 'Yearly')],
        default='month'
    )
    metric_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    department = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
