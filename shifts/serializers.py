from rest_framework import serializers
from .models import Shift, ShiftTemplate, ShiftSchedule
from users.serializers import UserSerializer


class ShiftSerializer(serializers.ModelSerializer):
    """Serializer for Shift model"""
    duration_hours = serializers.ReadOnlyField()
    total_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = Shift
        fields = [
            'id', 'name', 'start_time', 'end_time', 'break_duration',
            'is_active', 'duration_hours', 'total_hours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate shift times"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError(
                    "End time must be after start time"
                )
        
        return data


class ShiftTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ShiftTemplate model"""
    shift = ShiftSerializer(read_only=True)
    shift_id = serializers.IntegerField(write_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ShiftTemplate
        fields = [
            'id', 'name', 'shift', 'shift_id', 'frequency',
            'start_date', 'end_date', 'is_active', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate template dates"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date > end_date:
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        
        return data


class ShiftScheduleSerializer(serializers.ModelSerializer):
    """Serializer for ShiftSchedule model"""
    employee = UserSerializer(read_only=True)
    employee_id = serializers.IntegerField(write_only=True)
    shift = ShiftSerializer(read_only=True)
    shift_id = serializers.IntegerField(write_only=True)
    template = ShiftTemplateSerializer(read_only=True)
    template_id = serializers.IntegerField(write_only=True, required=False)
    created_by = UserSerializer(read_only=True)
    
    # Computed properties
    is_today = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    can_start = serializers.ReadOnlyField()
    can_end = serializers.ReadOnlyField()
    
    class Meta:
        model = ShiftSchedule
        fields = [
            'id', 'employee', 'employee_id', 'shift', 'shift_id',
            'date', 'status', 'template', 'template_id', 'notes',
            'created_by', 'created_at', 'updated_at',
            'is_today', 'is_overdue', 'can_start', 'can_end'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at',
            'is_today', 'is_overdue', 'can_start', 'can_end'
        ]

    def validate(self, data):
        """Validate schedule data"""
        employee = data.get('employee_id')
        date = data.get('date')
        
        if employee and date:
            # Check for existing shift on same date
            existing = ShiftSchedule.objects.filter(
                employee_id=employee, 
                date=date
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise serializers.ValidationError(
                    "Employee already has a shift scheduled on this date"
                )
        
        return data


class ShiftScheduleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ShiftSchedule instances"""
    employee_id = serializers.IntegerField()
    shift_id = serializers.IntegerField()
    template_id = serializers.IntegerField(required=False)
    
    class Meta:
        model = ShiftSchedule
        fields = [
            'employee_id', 'shift_id', 'date', 'status',
            'template_id', 'notes'
        ]

    def create(self, validated_data):
        """Create shift schedule with proper user assignment"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        
        return super().create(validated_data)


class ShiftScheduleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating ShiftSchedule instances"""
    class Meta:
        model = ShiftSchedule
        fields = [
            'date', 'status', 'notes'
        ]

    def validate_status(self, value):
        """Validate status transitions"""
        instance = self.instance
        if instance:
            current_status = instance.status
            
            # Define allowed status transitions
            allowed_transitions = {
                'scheduled': ['in_progress', 'cancelled'],
                'in_progress': ['completed', 'cancelled'],
                'completed': [],  # No further transitions
                'cancelled': [],  # No further transitions
                'no_show': []     # No further transitions
            }
            
            if value not in allowed_transitions.get(current_status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {current_status} to {value}"
                )
        
        return value


class ShiftBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating shift schedules"""
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    shift_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    template_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validate bulk create data"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date > end_date:
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        
        return data


class ShiftConflictSerializer(serializers.Serializer):
    """Serializer for shift conflict information"""
    employee_id = serializers.IntegerField()
    employee_name = serializers.CharField()
    conflict_date = serializers.DateField()
    conflict_type = serializers.CharField()  # 'shift' or 'attendance'
    existing_record = serializers.CharField()


class ShiftReportSerializer(serializers.Serializer):
    """Serializer for shift reports"""
    total_shifts = serializers.IntegerField()
    completed_shifts = serializers.IntegerField()
    cancelled_shifts = serializers.IntegerField()
    no_show_shifts = serializers.IntegerField()
    total_hours = serializers.FloatField()
    average_hours_per_shift = serializers.FloatField()
    date_range = serializers.CharField()
    employee_count = serializers.IntegerField()


class ShiftSummarySerializer(serializers.Serializer):
    """Serializer for shift summary"""
    today_shifts = serializers.IntegerField()
    upcoming_shifts = serializers.IntegerField()
    overdue_shifts = serializers.IntegerField()
    active_employees = serializers.IntegerField()
    total_hours_today = serializers.FloatField()
