from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('hr', 'HR/Admin'),
        ('manager', 'Team Manager'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    employee_id = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[RegexValidator(r'^[A-Z0-9]+$', 'Employee ID must contain only uppercase letters and numbers.')],
        help_text="Unique employee identifier (e.g., EMP001)"
    )
    phone_number = models.CharField(
        max_length=15, 
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Enter a valid phone number.')],
        blank=True
    )
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    face_encoding = models.TextField(blank=True, help_text="Face recognition encoding data")
    
    # Manager relationship
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'employee_id']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def is_hr_or_admin(self):
        return self.role in ['hr', 'manager']
    
    def can_manage_attendance(self):
        return self.role in ['hr', 'manager']
    
    def can_approve_leave(self):
        return self.role in ['hr', 'manager']
