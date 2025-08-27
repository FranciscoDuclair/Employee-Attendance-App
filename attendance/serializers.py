from rest_framework import serializers
from django.utils import timezone
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for attendance records"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    hours_worked = serializers.ReadOnlyField()
    is_late = serializers.ReadOnlyField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'user', 'user_name', 'employee_id', 'date', 'check_in_time',
            'check_out_time', 'attendance_type', 'status', 'face_verified',
            'face_confidence', 'is_manual', 'manual_approved_by', 'manual_reason',
            'latitude', 'longitude', 'notes', 'hours_worked', 'is_late',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_name', 'employee_id']


class CheckInSerializer(serializers.Serializer):
    """Serializer for check-in attendance"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        today = timezone.now().date()
        
        # Check if user already checked in today
        existing_checkin = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type='check_in'
        ).first()
        
        if existing_checkin:
            raise serializers.ValidationError("You have already checked in today.")
        
        return attrs


class CheckOutSerializer(serializers.Serializer):
    """Serializer for check-out attendance"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        today = timezone.now().date()
        
        # Check if user has checked in today
        checkin_record = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type='check_in'
        ).first()
        
        if not checkin_record:
            raise serializers.ValidationError("You must check in before checking out.")
        
        # Check if user already checked out today
        existing_checkout = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type='check_out'
        ).first()
        
        if existing_checkout:
            raise serializers.ValidationError("You have already checked out today.")
        
        return attrs


class FaceRecognitionSerializer(serializers.Serializer):
    """Serializer for face recognition check-in/out"""
    image = serializers.ImageField()
    attendance_type = serializers.ChoiceField(choices=['check_in', 'check_out'])
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        user = self.context['request'].user
        today = timezone.now().date()
        attendance_type = attrs['attendance_type']
        
        # Check existing attendance for the day
        existing_attendance = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type=attendance_type
        ).first()
        
        if existing_attendance:
            raise serializers.ValidationError(f"You have already {attendance_type.replace('_', ' ')} today.")
        
        # For check-out, ensure check-in exists
        if attendance_type == 'check_out':
            checkin_record = Attendance.objects.filter(
                user=user,
                date=today,
                attendance_type='check_in'
            ).first()
            
            if not checkin_record:
                raise serializers.ValidationError("You must check in before checking out.")
        
        return attrs


class ManualAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for manual attendance entry (HR/Admin only)"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    approved_by_name = serializers.CharField(source='manual_approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'user', 'user_name', 'employee_id', 'date', 'check_in_time',
            'check_out_time', 'attendance_type', 'status', 'is_manual',
            'manual_approved_by', 'approved_by_name', 'manual_reason',
            'latitude', 'longitude', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_manual', 'manual_approved_by', 'approved_by_name',
            'created_at', 'updated_at', 'user_name', 'employee_id'
        ]
    
    def create(self, validated_data):
        validated_data['is_manual'] = True
        validated_data['manual_approved_by'] = self.context['request'].user
        return super().create(validated_data)


class AttendanceHistorySerializer(serializers.ModelSerializer):
    """Serializer for attendance history"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    hours_worked = serializers.ReadOnlyField()
    is_late = serializers.ReadOnlyField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'user_name', 'employee_id', 'date', 'check_in_time',
            'check_out_time', 'attendance_type', 'status', 'face_verified',
            'is_manual', 'hours_worked', 'is_late', 'notes'
        ]


class AttendanceStatsSerializer(serializers.Serializer):
    """Serializer for attendance statistics"""
    total_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    total_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    average_hours_per_day = serializers.DecimalField(max_digits=6, decimal_places=2)
    punctuality_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
