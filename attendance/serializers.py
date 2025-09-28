from rest_framework import serializers
from .models import Attendance, AttendanceSettings
from users.serializers import UserSerializer


class AttendanceSerializer(serializers.ModelSerializer):
    """Serializer for attendance records"""
    user = UserSerializer(read_only=True)
    hours_worked = serializers.ReadOnlyField()
    is_late = serializers.ReadOnlyField()
    is_face_verified = serializers.ReadOnlyField()
    location_string = serializers.ReadOnlyField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'user', 'date', 'check_in_time', 'check_out_time',
            'attendance_type', 'status', 'face_verified', 'face_confidence',
            'face_image', 'latitude', 'longitude', 'location_accuracy',
            'notes', 'ip_address', 'device_info', 'hours_worked', 'is_late',
            'is_face_verified', 'location_string', 'created_at', 'updated_at'
        ]


class AttendanceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating attendance records"""
    
    class Meta:
        model = Attendance
        fields = [
            'user', 'date', 'check_in_time', 'check_out_time',
            'attendance_type', 'status', 'face_verified', 'face_confidence',
            'face_image', 'latitude', 'longitude', 'location_accuracy',
            'notes', 'ip_address', 'device_info'
        ]
    
    def validate(self, data):
        """Custom validation for attendance records"""
        user = data.get('user')
        date = data.get('date')
        attendance_type = data.get('attendance_type')
        
        # Check for duplicate records
        if Attendance.objects.filter(
            user=user,
            date=date,
            attendance_type=attendance_type
        ).exists():
            raise serializers.ValidationError(
                f"Attendance record for {attendance_type} already exists for this date."
            )
        
        return data


class AttendanceListSerializer(serializers.ModelSerializer):
    """Simplified serializer for attendance lists"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='user.employee_id', read_only=True)
    hours_worked = serializers.ReadOnlyField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'user_name', 'employee_id', 'date', 'check_in_time',
            'check_out_time', 'status', 'hours_worked', 'attendance_type',
            'face_verified', 'face_confidence'
        ]


class AttendanceSettingsSerializer(serializers.ModelSerializer):
    """Serializer for attendance settings"""
    
    class Meta:
        model = AttendanceSettings
        fields = [
            'face_recognition_enabled', 'face_confidence_threshold',
            'location_tracking_enabled', 'location_radius_meters',
            'office_latitude', 'office_longitude', 'late_threshold_minutes',
            'early_departure_threshold_minutes', 'require_photo_for_attendance',
            'allow_manual_attendance', 'created_at', 'updated_at'
        ]
