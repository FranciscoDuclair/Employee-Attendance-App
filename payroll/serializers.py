from rest_framework import serializers
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Payroll
from users.models import User
from attendance.models import Attendance


class PayrollSerializer(serializers.ModelSerializer):
    """Main payroll serializer"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    department = serializers.CharField(source='user.department', read_only=True)
    position = serializers.CharField(source='user.position', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'user', 'user_name', 'employee_id', 'department', 'position',
            'month', 'year', 'basic_salary', 'hourly_rate', 'total_hours_worked',
            'regular_hours', 'overtime_hours', 'regular_pay', 'overtime_pay',
            'tax_deduction', 'other_deductions', 'gross_pay', 'net_pay',
            'status', 'approved_by', 'approved_by_name', 'approved_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_hours_worked', 'regular_hours', 'overtime_hours',
            'regular_pay', 'overtime_pay', 'gross_pay', 'net_pay',
            'created_at', 'updated_at'
        ]


class PayrollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payroll records"""
    
    class Meta:
        model = Payroll
        fields = [
            'user', 'month', 'year', 'basic_salary', 'hourly_rate',
            'tax_deduction', 'other_deductions', 'status'
        ]
    
    def validate(self, data):
        """Validate payroll data"""
        user = data['user']
        month = data['month']
        year = data['year']
        
        # Check if payroll already exists for this user/month/year
        if Payroll.objects.filter(user=user, month=month, year=year).exists():
            raise serializers.ValidationError(
                f"Payroll record already exists for {user.get_full_name()} - {month}/{year}"
            )
        
        # Validate month and year
        if month < 1 or month > 12:
            raise serializers.ValidationError("Month must be between 1 and 12")
        
        if year < 2000 or year > 2100:
            raise serializers.ValidationError("Year must be between 2000 and 2100")
        
        return data


class PayrollUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating payroll records"""
    
    class Meta:
        model = Payroll
        fields = [
            'basic_salary', 'hourly_rate', 'tax_deduction', 'other_deductions',
            'status', 'approved_by'
        ]
    
    def validate_status(self, value):
        """Validate status changes"""
        if value == 'approved' and not self.context.get('request').user.can_manage_attendance():
            raise serializers.ValidationError("Only HR and Managers can approve payroll")
        return value


class PayrollCalculationSerializer(serializers.Serializer):
    """Serializer for payroll calculation requests"""
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    recalculate = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate calculation request"""
        user = data['user']
        month = data['month']
        year = data['year']
        
        # Check if payroll exists and recalculate is not requested
        if Payroll.objects.filter(user=user, month=month, year=year).exists() and not data.get('recalculate'):
            raise serializers.ValidationError(
                f"Payroll already exists for {user.get_full_name()} - {month}/{year}. Use recalculate=True to recalculate."
            )
        
        return data


class PayrollReportSerializer(serializers.Serializer):
    """Serializer for payroll report requests"""
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)
    department = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=Payroll.STATUS_CHOICES, required=False)
    export_format = serializers.ChoiceField(choices=['json', 'csv', 'pdf'], default='json')


class PayrollSummarySerializer(serializers.Serializer):
    """Serializer for payroll summary data"""
    total_employees = serializers.IntegerField()
    total_payroll_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_salary = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_overtime_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_overtime_pay = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_tax_deductions = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_other_deductions = serializers.DecimalField(max_digits=12, decimal_places=2)


class PayrollBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk payroll actions"""
    payroll_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=['approve', 'reject', 'delete'])
    notes = serializers.CharField(required=False, allow_blank=True)


class PayrollExportSerializer(serializers.Serializer):
    """Serializer for payroll export requests"""
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)
    department = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=Payroll.STATUS_CHOICES, required=False)
    format = serializers.ChoiceField(choices=['csv', 'pdf', 'excel'], default='csv')
    include_details = serializers.BooleanField(default=True)


class PayrollAdjustmentSerializer(serializers.Serializer):
    """Serializer for payroll adjustments"""
    payroll_id = serializers.IntegerField()
    adjustment_type = serializers.ChoiceField(choices=[
        'bonus', 'deduction', 'correction', 'other'
    ])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(max_length=500)
    approved_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    
    def validate_amount(self, value):
        """Validate adjustment amount"""
        if value == 0:
            raise serializers.ValidationError("Adjustment amount cannot be zero")
        return value


class PayrollComparisonSerializer(serializers.Serializer):
    """Serializer for payroll comparison between periods"""
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    period1_month = serializers.IntegerField(min_value=1, max_value=12)
    period1_year = serializers.IntegerField(min_value=2000, max_value=2100)
    period2_month = serializers.IntegerField(min_value=1, max_value=12)
    period2_year = serializers.IntegerField(min_value=2000, max_value=2100)
    
    def validate(self, data):
        """Validate comparison periods"""
        p1 = (data['period1_year'], data['period1_month'])
        p2 = (data['period2_year'], data['period2_month'])
        
        if p1 == p2:
            raise serializers.ValidationError("Cannot compare payroll with itself")
        
        return data


class PayrollTaxCalculationSerializer(serializers.Serializer):
    """Serializer for tax calculation requests"""
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    gross_pay = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_bracket = serializers.ChoiceField(choices=[
        'low', 'medium', 'high', 'custom'
    ], required=False)
    custom_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, 
        min_value=0, max_value=100, 
        required=False
    )
    
    def validate(self, data):
        """Validate tax calculation data"""
        if data.get('tax_bracket') == 'custom' and not data.get('custom_rate'):
            raise serializers.ValidationError("Custom rate is required when tax bracket is 'custom'")
        
        if data.get('custom_rate') and (data['custom_rate'] < 0 or data['custom_rate'] > 100):
            raise serializers.ValidationError("Custom tax rate must be between 0 and 100")
        
        return data
