import json
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from .models import Notification, NotificationTemplate
from .serializers import WebSocketNotificationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def send_real_time_notification(notification):
    """
    Send a real-time notification via WebSocket to a specific user
    """
    try:
        if not notification.user:
            logger.error("Notification has no user assigned")
            return False
        
        # Serialize notification for WebSocket
        serializer = WebSocketNotificationSerializer(notification)
        
        # Send to user's group
        user_group_name = f"user_{notification.user.id}"
        
        async_to_sync(channel_layer.group_send)(
            user_group_name,
            {
                'type': 'notification_message',
                'notification': serializer.data
            }
        )
        
        logger.info(f"Sent real-time notification to user {notification.user.get_full_name()}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending real-time notification: {str(e)}")
        return False


def create_and_send_notification(user, title, message, notification_type='general', 
                                priority='medium', **kwargs):
    """
    Create a notification and send it via WebSocket
    """
    try:
        # Create notification in database
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            **kwargs
        )
        
        # Send real-time notification
        send_real_time_notification(notification)
        
        return notification
        
    except Exception as e:
        logger.error(f"Error creating and sending notification: {str(e)}")
        return None


def send_attendance_notification(user, attendance_type, status='success'):
    """
    Send attendance-related notification
    """
    if attendance_type == 'check_in':
        title = "Check-in Successful"
        message = f"You have successfully checked in at {user.last_login.strftime('%H:%M')}"
    elif attendance_type == 'check_out':
        title = "Check-out Successful"
        message = f"You have successfully checked out at {user.last_login.strftime('%H:%M')}"
    else:
        title = "Attendance Updated"
        message = "Your attendance record has been updated"
    
    # Send to HR/Managers as well
    hr_users = User.objects.filter(role__in=['hr', 'manager'])
    
    # Notification to employee
    create_and_send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='attendance',
        priority='medium'
    )
    
    # Notification to HR/Managers
    for hr_user in hr_users:
        create_and_send_notification(
            user=hr_user,
            title=f"Employee {attendance_type.replace('_', ' ').title()}",
            message=f"{user.get_full_name()} has {attendance_type.replace('_', ' ')}",
            notification_type='attendance',
            priority='low'
        )


def send_leave_notification(leave_request, action='submitted'):
    """
    Send leave-related notifications
    """
    user = leave_request.user
    
    if action == 'submitted':
        # Notify employee
        create_and_send_notification(
            user=user,
            title="Leave Request Submitted",
            message=f"Your {leave_request.leave_type.name} request for {leave_request.start_date} to {leave_request.end_date} has been submitted",
            notification_type='leave',
            priority='medium',
            related_object_type='leave_request',
            related_object_id=leave_request.id
        )
        
        # Notify HR/Managers
        hr_users = User.objects.filter(role__in=['hr', 'manager'])
        for hr_user in hr_users:
            create_and_send_notification(
                user=hr_user,
                title="New Leave Request",
                message=f"{user.get_full_name()} has submitted a {leave_request.leave_type.name} request",
                notification_type='leave',
                priority='medium',
                related_object_type='leave_request',
                related_object_id=leave_request.id
            )
    
    elif action in ['approved', 'rejected']:
        priority = 'high' if action == 'approved' else 'medium'
        title = f"Leave Request {action.title()}"
        message = f"Your {leave_request.leave_type.name} request has been {action}"
        
        create_and_send_notification(
            user=user,
            title=title,
            message=message,
            notification_type='leave',
            priority=priority,
            related_object_type='leave_request',
            related_object_id=leave_request.id
        )


def send_shift_notification(shift_schedule, action='assigned'):
    """
    Send shift-related notifications
    """
    user = shift_schedule.employee
    
    if action == 'assigned':
        title = "New Shift Assigned"
        message = f"You have been assigned to {shift_schedule.shift.name} on {shift_schedule.date}"
        priority = 'medium'
    elif action == 'updated':
        title = "Shift Updated"
        message = f"Your shift on {shift_schedule.date} has been updated"
        priority = 'medium'
    elif action == 'cancelled':
        title = "Shift Cancelled"
        message = f"Your {shift_schedule.shift.name} shift on {shift_schedule.date} has been cancelled"
        priority = 'high'
    else:
        title = "Shift Notification"
        message = f"Shift update for {shift_schedule.date}"
        priority = 'medium'
    
    create_and_send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='shift',
        priority=priority,
        related_object_type='shift_schedule',
        related_object_id=shift_schedule.id
    )


def send_payroll_notification(payroll, action='generated'):
    """
    Send payroll-related notifications
    """
    user = payroll.user
    
    if action == 'generated':
        title = "Payroll Generated"
        message = f"Your payroll for {payroll.month}/{payroll.year} has been generated. Net pay: ${payroll.net_pay}"
        priority = 'high'
    elif action == 'approved':
        title = "Payroll Approved"
        message = f"Your payroll for {payroll.month}/{payroll.year} has been approved"
        priority = 'high'
    else:
        title = "Payroll Update"
        message = f"Your payroll for {payroll.month}/{payroll.year} has been updated"
        priority = 'medium'
    
    create_and_send_notification(
        user=user,
        title=title,
        message=message,
        notification_type='payroll',
        priority=priority,
        related_object_type='payroll',
        related_object_id=payroll.id
    )


def send_system_notification(users, title, message, priority='medium'):
    """
    Send system-wide notifications to multiple users
    """
    if not isinstance(users, list):
        users = [users]
    
    for user in users:
        create_and_send_notification(
            user=user,
            title=title,
            message=message,
            notification_type='system',
            priority=priority
        )


def send_broadcast_notification(title, message, user_roles=None, priority='medium'):
    """
    Send broadcast notification to all users or specific roles
    """
    if user_roles:
        users = User.objects.filter(role__in=user_roles, is_active=True)
    else:
        users = User.objects.filter(is_active=True)
    
    for user in users:
        create_and_send_notification(
            user=user,
            title=title,
            message=message,
            notification_type='system',
            priority=priority
        )


def create_notification_from_template(template_name, user, **context):
    """
    Create notification from a template
    """
    try:
        template = NotificationTemplate.objects.get(
            name=template_name,
            is_active=True
        )
        
        notification = template.render_notification(user, **context)
        send_real_time_notification(notification)
        
        return notification
        
    except NotificationTemplate.DoesNotExist:
        logger.error(f"Notification template '{template_name}' not found")
        return None


def send_bulk_notification(user_ids, title, message, notification_type='general', priority='medium'):
    """
    Send the same notification to multiple users efficiently
    """
    try:
        users = User.objects.filter(id__in=user_ids, is_active=True)
        
        notifications = []
        for user in users:
            notification = Notification(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority
            )
            notifications.append(notification)
        
        # Bulk create notifications
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Send real-time notifications
        for notification in created_notifications:
            send_real_time_notification(notification)
        
        logger.info(f"Sent bulk notification to {len(created_notifications)} users")
        return created_notifications
        
    except Exception as e:
        logger.error(f"Error sending bulk notification: {str(e)}")
        return []
