from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    """
    Model to store system notifications
    """
    TYPE_CHOICES = [
        ('attendance', 'Attendance'),
        ('leave', 'Leave'),
        ('payroll', 'Payroll'),
        ('shift', 'Shift'),
        ('system', 'System'),
        ('general', 'General'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Recipient
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # Notification content
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects (optional)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Action data
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save()


class NotificationTemplate(models.Model):
    """
    Model to store notification templates for different events
    """
    name = models.CharField(max_length=100, unique=True)
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    notification_type = models.CharField(max_length=20, choices=Notification.TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=Notification.PRIORITY_CHOICES, default='medium')
    
    # Template variables
    variables = models.JSONField(
        default=list,
        help_text="List of template variables that can be used in title and message"
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def render_notification(self, user, **context):
        """Render notification from template with context variables"""
        title = self.title_template.format(**context)
        message = self.message_template.format(**context)
        
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=self.notification_type,
            priority=self.priority
        )
