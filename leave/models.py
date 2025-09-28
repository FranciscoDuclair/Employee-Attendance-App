from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta

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
    
    def calculate_total_days(self):
        """Calculate total days excluding weekends"""
        if not self.start_date or not self.end_date:
            return 0
        
        current_date = self.start_date
        total_days = 0
        
        while current_date <= self.end_date:
            # Count only weekdays (Monday=0, Sunday=6)
            if current_date.weekday() < 5:  # Monday to Friday
                total_days += 1
            current_date += timedelta(days=1)
        
        return total_days

    def save(self, *args, **kwargs):
        # Auto-calculate total days
        self.total_days = self.calculate_total_days()
        
        # Set approved_at timestamp when status changes to approved
        if self.pk:
            original = LeaveRequest.objects.get(pk=self.pk)
            if original.status != 'approved' and self.status == 'approved':
                self.approved_at = timezone.now()
        elif self.status == 'approved':
            self.approved_at = timezone.now()
        
        self.clean()
        super().save(*args, **kwargs)
        
        # Update leave balance when approved
        if self.status == 'approved':
            self.update_leave_balance()

    def update_leave_balance(self):
        """Update user's leave balance when leave is approved"""
        # Only update if this is the first time being approved
        if not hasattr(self, '_balance_updated'):
            try:
                balance = LeaveBalance.objects.get(
                    user=self.user, 
                    leave_type=self.leave_type, 
                    year=self.start_date.year
                )
                balance.used_days += self.total_days
                balance.save()
            except LeaveBalance.DoesNotExist:
                # Create balance if it doesn't exist
                LeaveBalance.objects.create(
                    user=self.user,
                    leave_type=self.leave_type,
                    year=self.start_date.year,
                    total_allocated=self.leave_type.max_days_per_year if self.leave_type.max_days_per_year > 0 else 0,
                    used_days=self.total_days
                )
            self._balance_updated = True

    def clean(self):
        if self.start_date and self.end_date:
            # Basic date validation
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date.")
            
            # Prevent past dates (except for HR/Admin adjustments)
            if self.start_date < date.today() and not self.pk:
                raise ValidationError("Cannot request leave for past dates.")
            
            # Check for overlapping leave requests
            overlapping = LeaveRequest.objects.filter(
                user=self.user,
                status__in=['pending', 'approved'],
                start_date__lte=self.end_date,
                end_date__gte=self.start_date
            )
            
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            
            if overlapping.exists():
                overlapping_leave = overlapping.first()
                raise ValidationError(
                    f"Leave dates overlap with existing request: "
                    f"{overlapping_leave.start_date} to {overlapping_leave.end_date}"
                )
            
            # Check leave balance if leave type has max days
            if self.leave_type.max_days_per_year > 0:
                total_days = self.calculate_total_days()
                try:
                    balance = LeaveBalance.objects.get(
                        user=self.user,
                        leave_type=self.leave_type,
                        year=self.start_date.year
                    )
                    if balance.remaining_days < total_days:
                        raise ValidationError(
                            f"Insufficient leave balance. Available: {balance.remaining_days} days, "
                            f"Requested: {total_days} days"
                        )
                except LeaveBalance.DoesNotExist:
                    # No balance record, check against max allowed
                    if total_days > self.leave_type.max_days_per_year:
                        raise ValidationError(
                            f"Requested days ({total_days}) exceed maximum allowed "
                            f"({self.leave_type.max_days_per_year}) for {self.leave_type.name}"
                        )


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
        self.remaining_days = max(0, self.total_allocated - self.used_days)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_balance(cls, user, leave_type, year):
        """Get or create leave balance for user, leave type and year"""
        balance, created = cls.objects.get_or_create(
            user=user,
            leave_type=leave_type,
            year=year,
            defaults={
                'total_allocated': leave_type.max_days_per_year if leave_type.max_days_per_year > 0 else 0,
                'used_days': 0
            }
        )
        return balance, created
    
    @classmethod
    def allocate_annual_leave(cls, year):
        """Allocate annual leave for all active users"""
        from users.models import User
        
        active_users = User.objects.filter(is_active=True)
        active_leave_types = LeaveType.objects.filter(is_active=True, max_days_per_year__gt=0)
        
        allocated_count = 0
        for user in active_users:
            for leave_type in active_leave_types:
                balance, created = cls.get_or_create_balance(user, leave_type, year)
                if created:
                    allocated_count += 1
        
        return allocated_count
