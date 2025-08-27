from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Shift(models.Model):
    """
    Model to define work shifts
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_duration = models.PositiveIntegerField(
        default=0, 
        help_text="Break duration in minutes"
    )
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shifts'
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"
    
    @property
    def duration_hours(self):
        """Calculate shift duration in hours"""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        if end <= start:
            end += timedelta(days=1)
        duration = end - start
        return (duration.total_seconds() - (self.break_duration * 60)) / 3600


class ShiftSchedule(models.Model):
    """
    Model to schedule shifts for employees
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shift_schedules')
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Actual times (may differ from shift times)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Created by
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_schedules'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shift_schedules'
        unique_together = ['user', 'date']
        ordering = ['-date', 'shift__start_time']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.shift.name} on {self.date}"
    
    @property
    def actual_hours_worked(self):
        """Calculate actual hours worked"""
        if self.actual_start_time and self.actual_end_time:
            duration = self.actual_end_time - self.actual_start_time
            return duration.total_seconds() / 3600
        return 0
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.actual_start_time and self.actual_end_time and self.actual_start_time >= self.actual_end_time:
            raise ValidationError("Actual start time must be before actual end time.")


class ShiftTemplate(models.Model):
    """
    Model to create recurring shift templates
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='templates')
    
    # Recurrence pattern
    is_recurring = models.BooleanField(default=False)
    recurrence_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        blank=True
    )
    recurrence_days = models.JSONField(
        default=list,
        help_text="List of days (0=Monday, 6=Sunday) for weekly recurrence"
    )
    
    # Date range
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Assigned users
    assigned_users = models.ManyToManyField(
        User, 
        related_name='assigned_templates',
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_templates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shift_templates'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.shift.name}"
