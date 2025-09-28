import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';
import ApiService from '../../services/ApiService';

const { width } = Dimensions.get('window');

interface DashboardStats {
  todayAttendance: {
    status: 'not_checked_in' | 'checked_in' | 'checked_out';
    checkInTime?: string;
    checkOutTime?: string;
    totalHours?: string;
  };
  thisMonth: {
    totalDays: number;
    presentDays: number;
    absentDays: number;
    leaveDays: number;
  };
  leaveBalance: {
    annual: number;
    sick: number;
    personal: number;
  };
  upcomingShifts: any[];
  pendingLeaves: number;
}

export default function DashboardScreen() {
  const navigation = useNavigation();
  const { user } = useAuth();
  const { unreadCount } = useNotifications();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch dashboard statistics from API
      const [attendanceData, leaveData, shiftData] = await Promise.all([
        ApiService.getTodayAttendance(),
        ApiService.getLeaveBalance(),
        ApiService.getUpcomingShifts(),
      ]);

      setStats({
        todayAttendance: attendanceData || {
          status: 'not_checked_in',
        },
        thisMonth: {
          totalDays: 20,
          presentDays: 15,
          absentDays: 2,
          leaveDays: 3,
        },
        leaveBalance: leaveData || {
          annual: 15,
          sick: 10,
          personal: 5,
        },
        upcomingShifts: shiftData?.results || [],
        pendingLeaves: 2,
      });
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      Alert.alert('Error', 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'checkin':
        navigation.navigate('FaceRecognition', { mode: 'checkin' });
        break;
      case 'checkout':
        navigation.navigate('FaceRecognition', { mode: 'checkout' });
        break;
      case 'leave_request':
        navigation.navigate('LeaveRequest');
        break;
      case 'attendance_history':
        navigation.navigate('AttendanceHistory');
        break;
      case 'notifications':
        navigation.navigate('Notifications');
        break;
      default:
        break;
    }
  };

  const getAttendanceStatusColor = (status: string) => {
    switch (status) {
      case 'not_checked_in':
        return '#FF6B6B';
      case 'checked_in':
        return '#4ECDC4';
      case 'checked_out':
        return '#45B7D1';
      default:
        return '#999999';
    }
  };

  const getAttendanceStatusText = (status: string) => {
    switch (status) {
      case 'not_checked_in':
        return 'Not Checked In';
      case 'checked_in':
        return 'Checked In';
      case 'checked_out':
        return 'Checked Out';
      default:
        return 'Unknown';
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Loading dashboard...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Good morning,</Text>
          <Text style={styles.userName}>{user?.first_name || 'Employee'}</Text>
        </View>
        <TouchableOpacity
          style={styles.notificationButton}
          onPress={() => handleQuickAction('notifications')}
        >
          <Ionicons name="notifications-outline" size={24} color="#333333" />
          {unreadCount > 0 && (
            <View style={styles.notificationBadge}>
              <Text style={styles.notificationBadgeText}>
                {unreadCount > 99 ? '99+' : unreadCount}
              </Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* Today's Attendance */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Today's Attendance</Text>
        <View style={styles.attendanceContainer}>
          <View style={styles.attendanceStatus}>
            <View
              style={[
                styles.statusIndicator,
                { backgroundColor: getAttendanceStatusColor(stats?.todayAttendance.status || '') },
              ]}
            />
            <Text style={styles.statusText}>
              {getAttendanceStatusText(stats?.todayAttendance.status || '')}
            </Text>
          </View>
          
          {stats?.todayAttendance.checkInTime && (
            <Text style={styles.timeText}>
              Check-in: {stats.todayAttendance.checkInTime}
            </Text>
          )}
          
          {stats?.todayAttendance.checkOutTime && (
            <Text style={styles.timeText}>
              Check-out: {stats.todayAttendance.checkOutTime}
            </Text>
          )}
          
          {stats?.todayAttendance.totalHours && (
            <Text style={styles.totalHours}>
              Total: {stats.todayAttendance.totalHours}
            </Text>
          )}
        </View>
      </View>

      {/* Quick Actions */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quick Actions</Text>
        <View style={styles.quickActions}>
          {stats?.todayAttendance.status === 'not_checked_in' && (
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: '#4ECDC4' }]}
              onPress={() => handleQuickAction('checkin')}
            >
              <Ionicons name="log-in-outline" size={24} color="#FFFFFF" />
              <Text style={styles.actionButtonText}>Check In</Text>
            </TouchableOpacity>
          )}

          {stats?.todayAttendance.status === 'checked_in' && (
            <TouchableOpacity
              style={[styles.actionButton, { backgroundColor: '#45B7D1' }]}
              onPress={() => handleQuickAction('checkout')}
            >
              <Ionicons name="log-out-outline" size={24} color="#FFFFFF" />
              <Text style={styles.actionButtonText}>Check Out</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: '#FFA726' }]}
            onPress={() => handleQuickAction('leave_request')}
          >
            <Ionicons name="calendar-outline" size={24} color="#FFFFFF" />
            <Text style={styles.actionButtonText}>Request Leave</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionButton, { backgroundColor: '#66BB6A' }]}
            onPress={() => handleQuickAction('attendance_history')}
          >
            <Ionicons name="time-outline" size={24} color="#FFFFFF" />
            <Text style={styles.actionButtonText}>View History</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* This Month Summary */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>This Month</Text>
        <View style={styles.monthSummary}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>{stats?.thisMonth.presentDays}</Text>
            <Text style={styles.summaryLabel}>Present</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>{stats?.thisMonth.absentDays}</Text>
            <Text style={styles.summaryLabel}>Absent</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>{stats?.thisMonth.leaveDays}</Text>
            <Text style={styles.summaryLabel}>Leave</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryNumber}>{stats?.thisMonth.totalDays}</Text>
            <Text style={styles.summaryLabel}>Total</Text>
          </View>
        </View>
      </View>

      {/* Leave Balance */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Leave Balance</Text>
        <View style={styles.leaveBalance}>
          <View style={styles.leaveItem}>
            <Text style={styles.leaveType}>Annual</Text>
            <Text style={styles.leaveCount}>{stats?.leaveBalance.annual} days</Text>
          </View>
          <View style={styles.leaveItem}>
            <Text style={styles.leaveType}>Sick</Text>
            <Text style={styles.leaveCount}>{stats?.leaveBalance.sick} days</Text>
          </View>
          <View style={styles.leaveItem}>
            <Text style={styles.leaveType}>Personal</Text>
            <Text style={styles.leaveCount}>{stats?.leaveBalance.personal} days</Text>
          </View>
        </View>
      </View>

      {/* Upcoming Shifts */}
      {stats?.upcomingShifts && stats.upcomingShifts.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Upcoming Shifts</Text>
          {stats.upcomingShifts.slice(0, 3).map((shift, index) => (
            <View key={index} style={styles.shiftItem}>
              <Text style={styles.shiftDate}>{shift.date}</Text>
              <Text style={styles.shiftTime}>
                {shift.start_time} - {shift.end_time}
              </Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 20,
    backgroundColor: '#FFFFFF',
  },
  greeting: {
    fontSize: 16,
    color: '#666666',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333333',
  },
  notificationButton: {
    position: 'relative',
    padding: 8,
  },
  notificationBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: '#FF6B6B',
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  notificationBadgeText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: 'bold',
  },
  card: {
    backgroundColor: '#FFFFFF',
    margin: 15,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 15,
  },
  attendanceContainer: {
    alignItems: 'center',
  },
  attendanceStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 8,
  },
  statusText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
  },
  timeText: {
    fontSize: 14,
    color: '#666666',
    marginVertical: 2,
  },
  totalHours: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
    marginTop: 5,
  },
  quickActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: (width - 70) / 2,
    padding: 15,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 10,
  },
  actionButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 5,
  },
  monthSummary: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666666',
    marginTop: 4,
  },
  leaveBalance: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  leaveItem: {
    alignItems: 'center',
  },
  leaveType: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 4,
  },
  leaveCount: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333333',
  },
  shiftItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  shiftDate: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333333',
  },
  shiftTime: {
    fontSize: 14,
    color: '#666666',
  },
});
