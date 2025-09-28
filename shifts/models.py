from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from users.models import User


class Shift(models.Model):
    """Model for defining different types of shifts"""
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField(help_text="Shift start time (e.g., 09:00)")
    end_time = models.TimeField(help_text="Shift end time (e.g., 17:00)")
    break_duration = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(0), MaxValueValidator(480)],
        help_text="Break duration in minutes"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"

    @property
    def duration_hours(self):
        """Calculate shift duration in hours"""
        if self.start_time and self.end_time:
            start_dt = timezone.now().replace(
                hour=self.start_time.hour,
                minute=self.start_time.minute,
                second=0,
                microsecond=0
            )
            end_dt = timezone.now().replace(
                hour=self.end_time.hour,
                minute=self.end_time.minute,
                second=0,
                microsecond=0
            )
            
            if end_dt <= start_dt:
                end_dt += timezone.timedelta(days=1)
            
            duration = end_dt - start_dt
            return round(duration.total_seconds() / 3600, 2)
        return 0

    @property
    def total_hours(self):
        """Calculate total working hours including break"""
        return self.duration_hours - (self.break_duration / 60)


class ShiftTemplate(models.Model):
    """Model for recurring shift patterns"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    name = models.CharField(max_length=100)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='templates')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_shift_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Shift Template"
        verbose_name_plural = "Shift Templates"

    def __str__(self):
        return f"{self.name} - {self.shift.name} ({self.frequency})"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date must be after start date")


class ShiftSchedule(models.Model):
    """Model for individual shift assignments"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    employee = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='shift_schedules'
    )
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    template = models.ForeignKey(
        ShiftTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='schedules'
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_schedules'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'shift__start_time']
        unique_together = ['employee', 'date']
        verbose_name = "Shift Schedule"
        verbose_name_plural = "Shift Schedules"

    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.shift.name} on {self.date}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Check if employee already has a shift on this date
        if ShiftSchedule.objects.filter(
            employee=self.employee, 
            date=self.date
        ).exclude(pk=self.pk).exists():
            raise ValidationError("Employee already has a shift scheduled on this date")
        
        # Check if shift conflicts with existing attendance
        from attendance.models import Attendance
        if Attendance.objects.filter(
            employee=self.employee,
            date=self.date
        ).exists():
            raise ValidationError("Employee has attendance records for this date")

    @property
    def is_today(self):
        """Check if this shift is scheduled for today"""
        return self.date == timezone.now().date()

    @property
    def is_overdue(self):
        """Check if this shift is overdue"""
        return self.date < timezone.now().date() and self.status == 'scheduled'

    @property
    def can_start(self):
        """Check if this shift can be started"""
        if not self.is_today:
            return False
        
        now = timezone.now().time()
        return self.shift.start_time <= now <= self.shift.end_time

    @property
    def can_end(self):
        """Check if this shift can be ended"""
        if not self.is_today:
            return False
        
        now = timezone.now().time()
        return now >= self.shift.end_time

    def start_shift(self):
        """Mark shift as in progress"""
        if self.can_start and self.status == 'scheduled':
            self.status = 'in_progress'
            self.save()
            return True
        return False

    def complete_shift(self):
        """Mark shift as completed"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.save()
            return True
        return False

    def cancel_shift(self):
        """Cancel the shift"""
        if self.status in ['scheduled', 'in_progress']:
            self.status = 'cancelled'
            self.save()
            return True
        return False
