from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'notifications'

# Create router for ViewSets
router = DefaultRouter()

urlpatterns = [
    # Notification CRUD operations
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('create/', views.NotificationCreateView.as_view(), name='notification-create'),
    # Notification actions
    path('mark-read/', views.mark_notifications_read, name='mark-notifications-read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark-all-notifications-read'),
    path('unread-count/', views.unread_count, name='unread-count'),
    path('stats/', views.NotificationStatsView.as_view(), name='notification-stats'),
    path('delete-old/', views.delete_old_notifications, name='delete-old-notifications'),
    path('send-system-notification-web/', views.send_system_notification_web, name='send-system-notification-web'),
    path('templates/', views.NotificationTemplateListView.as_view(), name='notification-template-list'),
    path('send-message/', views.send_message, name='send_message'),
]
