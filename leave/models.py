from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class LeaveType(models.Model):
    """
    Model to define different types of leave
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    max_days_per_year = models.PositiveIntegerField(default=0, help_text="Maximum days allowed per year (0 for unlimited)")
    requires_approval = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leave_types'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """
    Model to track employee leave requests
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='requests')
    
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval information
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    # Emergency contact
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=15, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leave_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")


class LeaveBalance(models.Model):
    """
    Model to track employee leave balances
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    year = models.PositiveIntegerField()
    
    total_allocated = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)
    remaining_days = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leave_balances'
        unique_together = ['user', 'leave_type', 'year']
        ordering = ['-year', 'leave_type']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.leave_type.name} ({self.year})"
    
    def save(self, *args, **kwargs):
        self.remaining_days = self.total_allocated - self.used_days
        super().save(*args, **kwargs)
