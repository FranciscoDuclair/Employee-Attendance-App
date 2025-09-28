from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json

from .models import Notification, NotificationTemplate
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationMarkReadSerializer, NotificationTemplateSerializer
)


class NotificationListView(generics.ListAPIView):
    """List user's notifications with filtering and search"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'priority', 'is_read'] if DjangoFilterBackend else []
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a specific notification"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """Auto-mark notification as read when retrieved"""
        instance = self.get_object()
        if not instance.is_read:
            instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NotificationCreateView(generics.CreateAPIView):
    """Create new notification (Admin/HR only)"""
    serializer_class = NotificationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """Create notification and send via WebSocket"""
        notification = serializer.save()
        
        # Send real-time notification via WebSocket
        from .utils import send_real_time_notification
        send_real_time_notification(notification)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notifications_read(request):
    """Mark multiple notifications as read"""
    serializer = NotificationMarkReadSerializer(data=request.data)
    if serializer.is_valid():
        notification_ids = serializer.validated_data['notification_ids']
        
        # Update notifications for the authenticated user
        notifications = Notification.objects.filter(
            id__in=notification_ids,
            user=request.user,
            is_read=False
        )
        
        updated_count = 0
        for notification in notifications:
            notification.mark_as_read()
            updated_count += 1
        
        return Response({
            'message': f'Marked {updated_count} notifications as read',
            'updated_count': updated_count
        })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all user's notifications as read"""
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    )
    
    updated_count = 0
    for notification in notifications:
        notification.mark_as_read()
        updated_count += 1
    
    return Response({
        'message': f'Marked {updated_count} notifications as read',
        'updated_count': updated_count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """Get notification statistics for the user"""
    user = request.user
    
    # Get notification counts
    total_notifications = Notification.objects.filter(user=user).count()
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
    read_notifications = total_notifications - unread_notifications
    
    # Get notifications by type
    notifications_by_type = {}
    type_counts = Notification.objects.filter(user=user).values('notification_type').annotate(
        count=Count('id')
    )
    for item in type_counts:
        notifications_by_type[item['notification_type']] = item['count']
    
    # Get recent notifications (last 5)
    recent_notifications = Notification.objects.filter(user=user)[:5]
    
    stats_data = {
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
        'notifications_by_type': notifications_by_type,
        'recent_notifications': recent_notifications
    }
    
    serializer = NotificationStatsSerializer(stats_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    """Get unread notification count for the user"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return Response({'unread_count': count})


# Notification Template Views (Admin only)
class NotificationStatsView(APIView):
    """Get notification statistics for the user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get basic stats
        total_notifications = Notification.objects.filter(user=user).count()
        unread_notifications = Notification.objects.filter(user=user, is_read=False).count()
        read_notifications = total_notifications - unread_notifications
        
        # Get stats by type
        type_stats = {}
        for choice in Notification.TYPE_CHOICES:
            type_key = choice[0]
            type_count = Notification.objects.filter(user=user, notification_type=type_key).count()
            type_stats[type_key] = type_count
        
        return Response({
            'total': total_notifications,
            'unread': unread_notifications,
            'read': read_notifications,
            'by_type': type_stats
        })


class NotificationTemplateListView(generics.ListCreateAPIView):
    """List and create notification templates"""
    queryset = NotificationTemplate.objects.filter(is_active=True)
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Only admins can access templates"""
        if not self.request.user.can_manage_attendance():
            return NotificationTemplate.objects.none()
        return super().get_queryset()


class NotificationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete notification template"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_old_notifications(request):
    """Delete old read notifications (older than 30 days)"""
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    old_notifications = Notification.objects.filter(
        user=request.user,
        is_read=True,
        read_at__lt=cutoff_date
    )
    
    deleted_count = old_notifications.count()
    old_notifications.delete()
    
    return Response({
        'message': f'Deleted {deleted_count} old notifications',
        'deleted_count': deleted_count
    })


@csrf_exempt
@login_required
def send_message(request):
    """Send a message to a team member"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipient_id = data.get('recipient_id')
            message = data.get('message')
            
            if not recipient_id or not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Missing recipient_id or message'
                }, status=400)
            
            # Get recipient user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                recipient = User.objects.get(id=recipient_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Recipient not found'
                }, status=404)
            
            # Create notification
            notification = Notification.objects.create(
                user=recipient,
                title=f'Message from {request.user.get_full_name() or request.user.username}',
                message=message,
                notification_type='message',
                priority='medium',
                sender=request.user
            )
            
            # Send real-time notification if available
            try:
                from .utils import send_real_time_notification
                send_real_time_notification(notification)
            except ImportError:
                pass  # Real-time notifications not available
            
            return JsonResponse({
                'success': True,
                'message': 'Message sent successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    }, status=405)


@login_required
def send_system_notification_web(request):
    """Web-based system notification sending for HR/Admin"""
    user = request.user
    
    # Check if user can send system notifications
    if not user.can_manage_attendance():
        return JsonResponse({
            'success': False,
            'error': 'Only HR and Managers can send system notifications'
        }, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            title = data.get('title', '').strip()
            message = data.get('message', '').strip()
            recipients = data.get('recipients', 'all')
            urgent = data.get('urgent', False)
            
            if not title or not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Title and message are required'
                }, status=400)
            
            # Import User model
            from users.models import User
            
            # Determine recipients based on selection
            if recipients == 'employees':
                target_users = User.objects.filter(is_active=True, role='employee')
            elif recipients == 'managers':
                target_users = User.objects.filter(is_active=True, role='manager')
            elif recipients == 'hr':
                target_users = User.objects.filter(is_active=True, role='hr')
            else:  # 'all'
                target_users = User.objects.filter(is_active=True)
            
            # Create notifications for all target users
            notifications_created = 0
            for target_user in target_users:
                notification = Notification.objects.create(
                    user=target_user,
                    title=title,
                    message=message,
                    notification_type='system',
                    priority='high' if urgent else 'medium',
                    sender=user
                )
                notifications_created += 1
            
            return JsonResponse({
                'success': True,
                'message': f'System notification sent successfully',
                'count': notifications_created
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error sending notification: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': 'Method not allowed'
    }, status=405)
