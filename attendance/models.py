from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


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
        ('half_day', 'Half Day'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    attendance_type = models.CharField(max_length=10, choices=ATTENDANCE_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    
    # Face recognition data
    face_verified = models.BooleanField(default=False)
    face_confidence = models.FloatField(null=True, blank=True, help_text="Confidence score for face recognition")
    
    # Manual override
    is_manual = models.BooleanField(default=False)
    manual_approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='manual_approvals'
    )
    manual_reason = models.TextField(blank=True)
    
    # Location data (optional)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance'
        unique_together = ['user', 'date', 'attendance_type']
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.date} - {self.get_attendance_type_display()}"
    
    @property
    def hours_worked(self):
        """Calculate hours worked for the day"""
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            return duration.total_seconds() / 3600
        return 0
    
    @property
    def is_late(self):
        """Check if employee was late (assuming 9 AM start time)"""
        if self.check_in_time:
            expected_time = self.check_in_time.replace(hour=9, minute=0, second=0, microsecond=0)
            return self.check_in_time > expected_time
        return False
