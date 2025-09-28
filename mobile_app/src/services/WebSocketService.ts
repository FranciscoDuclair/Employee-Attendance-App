import AsyncStorage from '@react-native-async-storage/async-storage';
import { EventEmitter } from 'events';

interface NotificationData {
  id: number;
  title: string;
  message: string;
  type: string;
  data?: any;
  created_at: string;
  is_read: boolean;
}

interface WebSocketMessage {
  type: string;
  data: any;
}

class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  private isConnecting = false;
  private shouldReconnect = true;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private baseUrl: string;

  constructor() {
    super();
    this.baseUrl = 'ws://192.168.1.100:8000'; // Update with your server IP
  }

  async connect(): Promise<void> {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;

    try {
      const token = await AsyncStorage.getItem('auth_token');
      if (!token) {
        console.warn('No auth token found, cannot connect to WebSocket');
        this.isConnecting = false;
        return;
      }

      const wsUrl = `${this.baseUrl}/ws/notifications/?token=${token}`;
      console.log('Connecting to WebSocket:', wsUrl);

      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.isConnecting = false;
      this.handleReconnect();
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.isConnecting = false;
      this.stopHeartbeat();
      this.emit('disconnected', { code: event.code, reason: event.reason });

      if (this.shouldReconnect) {
        this.handleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.isConnecting = false;
      this.emit('error', error);
    };
  }

  private handleMessage(message: WebSocketMessage): void {
    console.log('Received WebSocket message:', message);

    switch (message.type) {
      case 'notification':
        this.handleNotification(message.data);
        break;
      case 'attendance_update':
        this.handleAttendanceUpdate(message.data);
        break;
      case 'leave_update':
        this.handleLeaveUpdate(message.data);
        break;
      case 'shift_update':
        this.handleShiftUpdate(message.data);
        break;
      case 'payroll_update':
        this.handlePayrollUpdate(message.data);
        break;
      case 'system_message':
        this.handleSystemMessage(message.data);
        break;
      case 'pong':
        // Heartbeat response
        break;
      default:
        console.warn('Unknown message type:', message.type);
        this.emit('message', message);
        break;
    }
  }

  private handleNotification(notification: NotificationData): void {
    console.log('New notification:', notification);
    this.emit('notification', notification);
  }

  private handleAttendanceUpdate(data: any): void {
    console.log('Attendance update:', data);
    this.emit('attendance_update', data);
  }

  private handleLeaveUpdate(data: any): void {
    console.log('Leave update:', data);
    this.emit('leave_update', data);
  }

  private handleShiftUpdate(data: any): void {
    console.log('Shift update:', data);
    this.emit('shift_update', data);
  }

  private handlePayrollUpdate(data: any): void {
    console.log('Payroll update:', data);
    this.emit('payroll_update', data);
  }

  private handleSystemMessage(data: any): void {
    console.log('System message:', data);
    this.emit('system_message', data);
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('max_reconnect_attempts_reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect();
      }
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendMessage({ type: 'ping' });
      }
    }, 30000); // Send ping every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  sendMessage(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected, cannot send message');
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getConnectionState(): string {
    if (!this.ws) return 'CLOSED';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'CLOSED';
      default:
        return 'UNKNOWN';
    }
  }

  // Utility methods for subscribing to specific events
  onNotification(callback: (notification: NotificationData) => void): () => void {
    this.on('notification', callback);
    return () => this.off('notification', callback);
  }

  onAttendanceUpdate(callback: (data: any) => void): () => void {
    this.on('attendance_update', callback);
    return () => this.off('attendance_update', callback);
  }

  onLeaveUpdate(callback: (data: any) => void): () => void {
    this.on('leave_update', callback);
    return () => this.off('leave_update', callback);
  }

  onShiftUpdate(callback: (data: any) => void): () => void {
    this.on('shift_update', callback);
    return () => this.off('shift_update', callback);
  }

  onPayrollUpdate(callback: (data: any) => void): () => void {
    this.on('payroll_update', callback);
    return () => this.off('payroll_update', callback);
  }

  onConnectionChange(callback: (status: string) => void): () => void {
    const handleConnect = () => callback('connected');
    const handleDisconnect = () => callback('disconnected');
    const handleError = () => callback('error');

    this.on('connected', handleConnect);
    this.on('disconnected', handleDisconnect);
    this.on('error', handleError);

    return () => {
      this.off('connected', handleConnect);
      this.off('disconnected', handleDisconnect);
      this.off('error', handleError);
    };
  }

  updateServerUrl(newUrl: string): void {
    this.baseUrl = newUrl;
    
    // Reconnect with new URL if currently connected
    if (this.isConnected()) {
      this.disconnect();
      setTimeout(() => this.connect(), 1000);
    }
  }
}

export default new WebSocketService();