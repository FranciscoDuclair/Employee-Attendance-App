from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import date, timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Attendance(models.Model):
    """
    Model to track employee attendance records
    """
    ATTENDANCE_TYPE_CHOICES = [
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
    ]
    
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('early_departure', 'Early Departure'),
    ]
    
    # Basic attendance information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=date.today)
    attendance_type = models.CharField(max_length=20, choices=ATTENDANCE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    
    # Time tracking
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    # Face recognition data
    face_verified = models.BooleanField(default=False)
    face_confidence = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Face recognition confidence score (0.0 - 1.0)"
    )
    face_image = models.ImageField(upload_to='attendance/faces/', null=True, blank=True)
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")
    
    # Additional information
    notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(blank=True, help_text="Device information for audit trail")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance'
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date', 'attendance_type']),
            models.Index(fields=['user', 'attendance_type', 'date']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_attendance_type_display()} on {self.date}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate hours worked if both check-in and check-out times are available
        if self.check_in_time and self.check_out_time:
            time_diff = self.check_out_time - self.check_in_time
            self.hours_worked = round(time_diff.total_seconds() / 3600, 2)
        
        # Auto-determine status based on check-in time
        if self.attendance_type == 'check_in' and self.check_in_time:
            self.status = self.determine_status()
        
        super().save(*args, **kwargs)
    
    def determine_status(self):
        """
        Determine attendance status based on check-in time and shift schedule
        """
        try:
            # Try to get user's shift for this date
            from shifts.models import ShiftSchedule
            shift_schedule = ShiftSchedule.objects.filter(
                employee=self.user,
                date=self.date
            ).first()
            
            if shift_schedule:
                shift_start = shift_schedule.shift.start_time
                check_in_time = self.check_in_time.time()
                
                # Define late threshold (15 minutes)
                late_threshold = timedelta(minutes=15)
                shift_start_datetime = timezone.now().replace(
                    hour=shift_start.hour,
                    minute=shift_start.minute,
                    second=0,
                    microsecond=0
                )
                late_time = (shift_start_datetime + late_threshold).time()
                
                if check_in_time <= shift_start:
                    return 'present'
                elif check_in_time <= late_time:
                    return 'late'
                else:
                    return 'late'  # Very late, but still present
            else:
                # No shift scheduled, use default business hours (9 AM)
                business_start = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0).time()
                late_time = timezone.now().replace(hour=9, minute=15, second=0, microsecond=0).time()
                check_in_time = self.check_in_time.time()
                
                if check_in_time <= business_start:
                    return 'present'
                elif check_in_time <= late_time:
                    return 'late'
                else:
                    return 'late'
                    
        except Exception as e:
            logger.warning(f"Error determining attendance status: {str(e)}")
            return 'present'  # Default to present if unable to determine
    
    @property
    def is_late(self):
        """Check if this attendance record indicates lateness"""
        return self.status == 'late'
    
    @property
    def is_face_verified(self):
        """Check if face verification was successful"""
        return self.face_verified and self.face_confidence and self.face_confidence >= 0.6
    
    @property
    def location_string(self):
        """Get formatted location string"""
        if self.latitude and self.longitude:
            return f"{self.latitude}, {self.longitude}"
        return "Location not available"
    
    @classmethod
    def get_today_attendance(cls, user):
        """Get today's attendance records for a user"""
        today = date.today()
        return cls.objects.filter(user=user, date=today)
    
    @classmethod
    def get_monthly_summary(cls, user, year, month):
        """Get monthly attendance summary for a user"""
        records = cls.objects.filter(
            user=user,
            date__year=year,
            date__month=month,
            attendance_type='check_in'
        )
        
        total_days = records.count()
        present_days = records.filter(status='present').count()
        late_days = records.filter(status='late').count()
        total_hours = sum([r.hours_worked for r in records if r.hours_worked])
        
        return {
            'total_days': total_days,
            'present_days': present_days,
            'late_days': late_days,
            'absent_days': 0,  # Would need to calculate based on working days
            'total_hours': round(total_hours, 2),
            'attendance_rate': round((present_days + late_days) / total_days * 100, 2) if total_days > 0 else 0
        }


class AttendanceSettings(models.Model):
    """
    Model to store attendance system settings
    """
    # Face recognition settings
    face_recognition_enabled = models.BooleanField(default=True)
    face_confidence_threshold = models.FloatField(
        default=0.6,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Minimum confidence score for face recognition (0.0 - 1.0)"
    )
    
    # Location settings
    location_tracking_enabled = models.BooleanField(default=False)
    location_radius_meters = models.PositiveIntegerField(
        default=100,
        help_text="Allowed radius from office location in meters"
    )
    office_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    office_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Time settings
    late_threshold_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Minutes after shift start time to mark as late"
    )
    early_departure_threshold_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Minutes before shift end time to mark as early departure"
    )
    
    # System settings
    require_photo_for_attendance = models.BooleanField(default=False)
    allow_manual_attendance = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance_settings'
        verbose_name = "Attendance Settings"
        verbose_name_plural = "Attendance Settings"
    
    def __str__(self):
        return f"Attendance Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    @classmethod
    def get_settings(cls):
        """Get or create attendance settings"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
