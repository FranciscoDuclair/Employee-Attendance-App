from rest_framework import serializers
from .models import Notification, NotificationTemplate


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'title', 'message', 'notification_type',
            'priority', 'is_read', 'read_at', 'related_object_type', 
            'related_object_id', 'action_url', 'action_text', 'created_at',
            'updated_at', 'time_ago'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'time_ago']
    
    def get_time_ago(self, obj):
        """Get human-readable time since notification was created"""
        from django.utils import timezone
        from datetime import datetime
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating notifications"""
    
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'notification_type', 'priority',
            'related_object_type', 'related_object_id', 'action_url', 'action_text'
        ]


class NotificationMarkReadSerializer(serializers.Serializer):
    """Serializer for marking notifications as read"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for NotificationTemplate model"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'title_template', 'message_template', 
            'notification_type', 'priority', 'variables', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics"""
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    read_notifications = serializers.IntegerField()
    notifications_by_type = serializers.DictField()
    recent_notifications = NotificationSerializer(many=True)


class WebSocketNotificationSerializer(serializers.ModelSerializer):
    """Serializer for WebSocket real-time notifications"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'title', 'message', 'notification_type',
            'priority', 'action_url', 'action_text', 'created_at'
        ]
