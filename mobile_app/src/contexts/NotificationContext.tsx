import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { Alert, Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import ApiService from '../services/ApiService';
import WebSocketService from '../services/WebSocketService';

interface NotificationData {
  id: number;
  title: string;
  message: string;
  type: string;
  data?: any;
  created_at: string;
  is_read: boolean;
}

interface NotificationContextType {
  notifications: NotificationData[];
  unreadCount: number;
  isLoading: boolean;
  refreshNotifications: () => Promise<void>;
  markAsRead: (notificationIds: number[]) => Promise<void>;
  markAllAsRead: () => Promise<void>;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

interface NotificationProviderProps {
  children: ReactNode;
}

// Configure notification handling
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

export function NotificationProvider({ children }: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<NotificationData[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    initializeNotifications();
    setupWebSocketListeners();
    setupNotificationListeners();

    return () => {
      cleanupListeners();
    };
  }, []);

  const initializeNotifications = async () => {
    try {
      // Request notification permissions
      const { status } = await Notifications.requestPermissionsAsync();
      if (status !== 'granted') {
        console.warn('Notification permissions not granted');
      }

      // Load initial notifications
      await refreshNotifications();
      await refreshUnreadCount();
    } catch (error) {
      console.error('Error initializing notifications:', error);
    }
  };

  const setupWebSocketListeners = () => {
    // Listen for real-time notifications
    WebSocketService.onNotification((notification: NotificationData) => {
      handleNewNotification(notification);
    });

    // Listen for other real-time updates
    WebSocketService.onAttendanceUpdate((data) => {
      console.log('Attendance update received:', data);
    });

    WebSocketService.onLeaveUpdate((data) => {
      console.log('Leave update received:', data);
    });

    WebSocketService.onShiftUpdate((data) => {
      console.log('Shift update received:', data);
    });

    WebSocketService.onPayrollUpdate((data) => {
      console.log('Payroll update received:', data);
    });
  };

  const setupNotificationListeners = () => {
    // Handle notification received while app is in foreground
    const notificationListener = Notifications.addNotificationReceivedListener(notification => {
      console.log('Notification received in foreground:', notification);
    });

    // Handle notification response (user tapped notification)
    const responseListener = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('Notification response:', response);
      handleNotificationTap(response.notification.request.content.data);
    });

    return () => {
      Notifications.removeNotificationSubscription(notificationListener);
      Notifications.removeNotificationSubscription(responseListener);
    };
  };

  const cleanupListeners = () => {
    // WebSocket listeners are cleaned up automatically by the service
  };

  const handleNewNotification = async (notification: NotificationData) => {
    try {
      // Add to local state
      setNotifications(prev => [notification, ...prev]);
      setUnreadCount(prev => prev + 1);

      // Show local push notification
      await Notifications.scheduleNotificationAsync({
        content: {
          title: notification.title,
          body: notification.message,
          data: notification.data,
          sound: true,
        },
        trigger: null, // Show immediately
      });

      // Update badge count
      await Notifications.setBadgeCountAsync(unreadCount + 1);
    } catch (error) {
      console.error('Error handling new notification:', error);
    }
  };

  const handleNotificationTap = (data: any) => {
    console.log('Notification tapped with data:', data);
    
    // Handle navigation based on notification type
    if (data?.type) {
      switch (data.type) {
        case 'attendance':
          // Navigate to attendance screen
          break;
        case 'leave':
          // Navigate to leave screen
          break;
        case 'shift':
          // Navigate to shift screen
          break;
        case 'payroll':
          // Navigate to payroll screen
          break;
        default:
          // Navigate to notifications screen
          break;
      }
    }
  };

  const refreshNotifications = async (): Promise<void> => {
    try {
      setIsLoading(true);
      const response = await ApiService.getNotifications({ page: 1 });
      setNotifications(response.results || []);
    } catch (error) {
      console.error('Error refreshing notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUnreadCount = async (): Promise<void> => {
    try {
      const count = await ApiService.getUnreadCount();
      setUnreadCount(count);
      await Notifications.setBadgeCountAsync(count);
    } catch (error) {
      console.error('Error refreshing unread count:', error);
    }
  };

  const markAsRead = async (notificationIds: number[]): Promise<void> => {
    try {
      await ApiService.markNotificationsRead(notificationIds);
      
      // Update local state
      setNotifications(prev => 
        prev.map(notification => 
          notificationIds.includes(notification.id)
            ? { ...notification, is_read: true }
            : notification
        )
      );

      // Update unread count
      const newUnreadCount = notifications.filter(n => 
        !n.is_read && !notificationIds.includes(n.id)
      ).length;
      setUnreadCount(newUnreadCount);
      await Notifications.setBadgeCountAsync(newUnreadCount);
    } catch (error) {
      console.error('Error marking notifications as read:', error);
    }
  };

  const markAllAsRead = async (): Promise<void> => {
    try {
      const unreadIds = notifications
        .filter(n => !n.is_read)
        .map(n => n.id);

      if (unreadIds.length > 0) {
        await markAsRead(unreadIds);
      }
    } catch (error) {
      console.error('Error marking all notifications as read:', error);
    }
  };

  const value: NotificationContextType = {
    notifications,
    unreadCount,
    isLoading,
    refreshNotifications,
    markAsRead,
    markAllAsRead,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications(): NotificationContextType {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
}
