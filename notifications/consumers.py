import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications
    """
    
    async def connect(self):
        """Accept WebSocket connection and authenticate user"""
        try:
            # Get user from scope (set by JWT middleware)
            user = self.scope['user']
            
            if user and not isinstance(user, AnonymousUser):
                self.user = user
                self.user_group_name = f"user_{user.id}"
                
                # Join user-specific notification group
                await self.channel_layer.group_add(
                    self.user_group_name,
                    self.channel_name
                )
                
                await self.accept()
                
                # Send connection confirmation
                await self.send(text_data=json.dumps({
                    'type': 'connection_established',
                    'message': 'Connected to notification system',
                    'user_id': user.id,
                    'user_name': user.get_full_name()
                }))
                
                logger.info(f"User {user.get_full_name()} connected to notifications WebSocket")
                
            else:
                logger.warning("Unauthenticated WebSocket connection attempt")
                await self.close(code=4001)  # Custom close code for authentication failure
                
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {str(e)}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
            if hasattr(self, 'user'):
                logger.info(f"User {self.user.get_full_name()} disconnected from notifications WebSocket")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
                
            elif message_type == 'mark_read':
                # Handle mark notification as read
                notification_id = text_data_json.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
                    
            elif message_type == 'get_unread_count':
                # Send current unread count
                count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': count
                }))
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received in WebSocket")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
    
    async def notification_message(self, event):
        """Handle notification message from group"""
        try:
            # Send notification to WebSocket
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'notification': event['notification']
            }))
        except Exception as e:
            logger.error(f"Error sending notification via WebSocket: {str(e)}")
    
    async def attendance_marked(self, event):
        """Handle attendance marked notification"""
        await self.send(text_data=json.dumps({
            'type': 'attendance_marked',
            'message': event['message'],
            'data': event.get('data', {})
        }))
    
    async def leave_response(self, event):
        """Handle leave approval/rejection notification"""
        await self.send(text_data=json.dumps({
            'type': 'leave_response',
            'message': event['message'],
            'status': event.get('status'),
            'data': event.get('data', {})
        }))
    
    async def shift_assigned(self, event):
        """Handle shift assignment notification"""
        await self.send(text_data=json.dumps({
            'type': 'shift_assigned',
            'message': event['message'],
            'data': event.get('data', {})
        }))
    
    async def payroll_generated(self, event):
        """Handle payroll generation notification"""
        await self.send(text_data=json.dumps({
            'type': 'payroll_generated',
            'message': event['message'],
            'data': event.get('data', {})
        }))
    
    async def system_notification(self, event):
        """Handle system-wide notifications"""
        await self.send(text_data=json.dumps({
            'type': 'system_notification',
            'message': event['message'],
            'priority': event.get('priority', 'medium'),
            'data': event.get('data', {})
        }))
    

    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read in database"""
        try:
            from .models import Notification
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            logger.error(f"Notification {notification_id} not found for user {self.user.id}")
            return False
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for user"""
        try:
            from .models import Notification
            return Notification.objects.filter(
                user=self.user,
                is_read=False
            ).count()
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0
