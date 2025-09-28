import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';

// API Configuration
const API_BASE_URL = 'http://192.168.4.27:8000/api'; // Update with your server IP
const API_TIMEOUT = 30000;

// Storage keys
const TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_DATA_KEY = 'user_data';

interface AuthTokens {
  access: string;
  refresh: string;
}

interface UserData {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  department: string;
  employee_id: string;
}

class ApiService {
  private api: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (reason?: any) => void;
  }> = [];

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem(TOKEN_KEY);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then(() => {
              return this.api(originalRequest);
            }).catch((err) => {
              return Promise.reject(err);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
            if (refreshToken) {
              const response = await this.refreshAuthToken(refreshToken);
              await AsyncStorage.setItem(TOKEN_KEY, response.data.access);
              
              this.processQueue(null);
              return this.api(originalRequest);
            }
          } catch (refreshError) {
            this.processQueue(refreshError);
            await this.logout();
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private processQueue(error: any) {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve();
      }
    });
    
    this.failedQueue = [];
  }

  // Authentication Methods
  async login(username: string, password: string): Promise<{ user: UserData; tokens: AuthTokens }> {
    try {
      const response = await this.api.post('/auth/login/', {
        username,
        password,
      });

      const { user, access, refresh } = response.data;

      // Store tokens and user data
      await AsyncStorage.setItem(TOKEN_KEY, access);
      await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refresh);
      await AsyncStorage.setItem(USER_DATA_KEY, JSON.stringify(user));

      return {
        user,
        tokens: { access, refresh },
      };
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      // Call logout endpoint if token exists
      const token = await AsyncStorage.getItem(TOKEN_KEY);
      if (token) {
        await this.api.post('/auth/logout/');
      }
    } catch (error) {
      console.warn('Logout API call failed:', error);
    } finally {
      // Clear local storage regardless of API call result
      await AsyncStorage.multiRemove([TOKEN_KEY, REFRESH_TOKEN_KEY, USER_DATA_KEY]);
    }
  }

  async refreshAuthToken(refreshToken: string): Promise<AxiosResponse> {
    return this.api.post('/auth/token/refresh/', {
      refresh: refreshToken,
    });
  }

  async getCurrentUser(): Promise<UserData | null> {
    try {
      const userData = await AsyncStorage.getItem(USER_DATA_KEY);
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error('Error getting current user:', error);
      return null;
    }
  }

  async isAuthenticated(): Promise<boolean> {
    try {
      const token = await AsyncStorage.getItem(TOKEN_KEY);
      return !!token;
    } catch (error) {
      return false;
    }
  }

  // Attendance Methods
  async checkIn(data: {
    latitude?: number;
    longitude?: number;
    notes?: string;
    face_image?: string;
  }): Promise<any> {
    try {
      const response = await this.api.post('/attendance/checkin/', data);
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async checkOut(data: {
    latitude?: number;
    longitude?: number;
    notes?: string;
  }): Promise<any> {
    try {
      const response = await this.api.post('/attendance/checkout/', data);
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getAttendanceHistory(params?: {
    start_date?: string;
    end_date?: string;
    page?: number;
  }): Promise<any> {
    try {
      const response = await this.api.get('/attendance/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getTodayAttendance(): Promise<any> {
    try {
      const response = await this.api.get('/attendance/today/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Leave Methods
  async getLeaveRequests(params?: {
    status?: string;
    page?: number;
  }): Promise<any> {
    try {
      const response = await this.api.get('/leave/requests/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async createLeaveRequest(data: {
    leave_type: number;
    start_date: string;
    end_date: string;
    reason: string;
    emergency_contact?: string;
    emergency_phone?: string;
  }): Promise<any> {
    try {
      const response = await this.api.post('/leave/requests/', data);
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getLeaveTypes(): Promise<any> {
    try {
      const response = await this.api.get('/leave/types/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getLeaveBalance(): Promise<any> {
    try {
      const response = await this.api.get('/leave/balance/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Shift Methods
  async getMyShifts(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    try {
      const response = await this.api.get('/shifts/my-shifts/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getShiftCalendar(params?: {
    month?: number;
    year?: number;
  }): Promise<any> {
    try {
      const response = await this.api.get('/shifts/calendar/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Payroll Methods
  async getPayrollHistory(params?: {
    year?: number;
    page?: number;
  }): Promise<any> {
    try {
      const response = await this.api.get('/payroll/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getCurrentPayroll(): Promise<any> {
    try {
      const response = await this.api.get('/payroll/current/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Notification Methods
  async getNotifications(params?: {
    is_read?: boolean;
    page?: number;
  }): Promise<any> {
    try {
      const response = await this.api.get('/notifications/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async markNotificationsRead(notificationIds: number[]): Promise<any> {
    try {
      const response = await this.api.post('/notifications/mark-read/', {
        notification_ids: notificationIds,
      });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getUnreadCount(): Promise<number> {
    try {
      const response = await this.api.get('/notifications/unread-count/');
      return response.data.unread_count;
    } catch (error) {
      this.handleApiError(error);
      return 0;
    }
  }

  // Report Methods
  async generateReport(data: {
    report_type: string;
    format: string;
    filters: any;
  }): Promise<any> {
    try {
      const response = await this.api.post('/reports/executions/', data);
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getReportStatus(executionId: number): Promise<any> {
    try {
      const response = await this.api.get(`/reports/executions/${executionId}/`);
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async downloadReport(executionId: number): Promise<any> {
    try {
      const response = await this.api.get(
        `/reports/executions/${executionId}/download/`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Dashboard Methods
  async getDashboardData(): Promise<any> {
    try {
      const response = await this.api.get('/reports/analytics/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async getAttendanceAnalytics(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    try {
      const response = await this.api.get('/reports/analytics/attendance/', { params });
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Profile Methods
  async updateProfile(data: {
    first_name?: string;
    last_name?: string;
    email?: string;
    phone?: string;
  }): Promise<any> {
    try {
      const response = await this.api.patch('/auth/profile/', data);
      
      // Update stored user data
      const currentUser = await this.getCurrentUser();
      if (currentUser) {
        const updatedUser = { ...currentUser, ...data };
        await AsyncStorage.setItem(USER_DATA_KEY, JSON.stringify(updatedUser));
      }
      
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async changePassword(data: {
    old_password: string;
    new_password: string;
  }): Promise<any> {
    try {
      const response = await this.api.post('/auth/change-password/', data);
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Face Recognition Methods
  async setupFaceRecognition(formData: FormData): Promise<any> {
    try {
      const response = await this.api.post('/attendance/face-setup/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return { success: true, ...response.data };
    } catch (error) {
      this.handleApiError(error);
      return { success: false, message: error.response?.data?.error || 'Face setup failed' };
    }
  }

  async faceRecognitionCheckIn(formData: FormData): Promise<any> {
    try {
      const response = await this.api.post('/attendance/face-checkin/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return { success: true, ...response.data };
    } catch (error) {
      this.handleApiError(error);
      return { success: false, message: error.response?.data?.error || 'Face check-in failed' };
    }
  }

  async faceRecognitionCheckOut(formData: FormData): Promise<any> {
    try {
      const response = await this.api.post('/attendance/face-checkout/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return { success: true, ...response.data };
    } catch (error) {
      this.handleApiError(error);
      return { success: false, message: error.response?.data?.error || 'Face check-out failed' };
    }
  }

  async getFaceRecognitionStatus(): Promise<any> {
    try {
      const response = await this.api.get('/attendance/face-status/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  async removeFaceRecognition(): Promise<any> {
    try {
      const response = await this.api.delete('/attendance/face-remove/');
      return response.data;
    } catch (error) {
      this.handleApiError(error);
      throw error;
    }
  }

  // Updated check-in method to support face recognition
  async checkIn(data: FormData | {
    latitude?: number;
    longitude?: number;
    location_accuracy?: number;
    notes?: string;
  }): Promise<any> {
    try {
      let response;
      if (data instanceof FormData) {
        // Face recognition check-in
        response = await this.faceRecognitionCheckIn(data);
      } else {
        // Regular check-in
        response = await this.api.post('/attendance/checkin/', data);
        response = { success: true, ...response.data };
      }
      return response;
    } catch (error) {
      this.handleApiError(error);
      return { success: false, message: error.response?.data?.error || 'Check-in failed' };
    }
  }

  // Updated check-out method to support face recognition
  async checkOut(data: FormData | {
    latitude?: number;
    longitude?: number;
    location_accuracy?: number;
    notes?: string;
  }): Promise<any> {
    try {
      let response;
      if (data instanceof FormData) {
        // Face recognition check-out
        response = await this.faceRecognitionCheckOut(data);
      } else {
        // Regular check-out
        response = await this.api.post('/attendance/checkout/', data);
        response = { success: true, ...response.data };
      }
      return response;
    } catch (error) {
      this.handleApiError(error);
      return { success: false, message: error.response?.data?.error || 'Check-out failed' };
    }
  }

  // Error Handling
  private handleApiError(error: any) {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          console.error('Bad Request:', data);
          break;
        case 401:
          console.error('Unauthorized:', data);
          break;
        case 403:
          console.error('Forbidden:', data);
          break;
        case 404:
          console.error('Not Found:', data);
          break;
        case 500:
          console.error('Server Error:', data);
          Alert.alert(
            'Server Error',
            'Something went wrong on our end. Please try again later.',
            [{ text: 'OK' }]
          );
          break;
        default:
          console.error('API Error:', status, data);
          break;
      }
    } else if (error.request) {
      // Network error
      console.error('Network Error:', error.request);
      Alert.alert(
        'Network Error',
        'Please check your internet connection and try again.',
        [{ text: 'OK' }]
      );
    } else {
      // Other error
      console.error('Error:', error.message);
    }
  }

  // Utility Methods
  async testConnection(): Promise<boolean> {
    try {
      await this.api.get('/auth/test/');
      return true;
    } catch (error) {
      return false;
    }
  }

  getApiUrl(): string {
    return API_BASE_URL;
  }

  updateApiUrl(newUrl: string): void {
    this.api.defaults.baseURL = newUrl;
  }
}

export default new ApiService();