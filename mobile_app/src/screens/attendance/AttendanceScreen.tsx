import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import ApiService from '../../services/ApiService';

interface TodayAttendance {
  id?: number;
  check_in_time?: string;
  check_out_time?: string;
  total_hours?: string;
  status: 'not_checked_in' | 'checked_in' | 'checked_out';
  location?: string;
}

interface AttendanceStats {
  this_week: {
    total_hours: string;
    days_present: number;
    days_absent: number;
  };
  this_month: {
    total_hours: string;
    days_present: number;
    days_absent: number;
    overtime_hours: string;
  };
}

export default function AttendanceScreen() {
  const navigation = useNavigation();
  const [todayAttendance, setTodayAttendance] = useState<TodayAttendance>({
    status: 'not_checked_in',
  });
  const [stats, setStats] = useState<AttendanceStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAttendanceData();
  }, []);

  const loadAttendanceData = async () => {
    try {
      setIsLoading(true);
      
      const [todayData, statsData] = await Promise.all([
        ApiService.getTodayAttendance(),
        ApiService.getAttendanceStats(),
      ]);

      setTodayAttendance(todayData || { status: 'not_checked_in' });
      setStats(statsData);
    } catch (error) {
      console.error('Error loading attendance data:', error);
      Alert.alert('Error', 'Failed to load attendance data');
    } finally {
      setIsLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadAttendanceData();
    setRefreshing(false);
  };

  const handleCheckIn = () => {
    navigation.navigate('FaceRecognition', { mode: 'checkin' });
  };

  const handleCheckOut = () => {
    navigation.navigate('FaceRecognition', { mode: 'checkout' });
  };

  const handleManualCheckIn = () => {
    Alert.alert(
      'Manual Check-in',
      'Are you sure you want to check in manually?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Check In',
          onPress: async () => {
            try {
              await ApiService.manualCheckIn();
              Alert.alert('Success', 'Manual check-in successful');
              await loadAttendanceData();
            } catch (error) {
              Alert.alert('Error', 'Manual check-in failed');
            }
          },
        },
      ]
    );
  };

  const handleManualCheckOut = () => {
    Alert.alert(
      'Manual Check-out',
      'Are you sure you want to check out manually?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Check Out',
          onPress: async () => {
            try {
              await ApiService.manualCheckOut();
              Alert.alert('Success', 'Manual check-out successful');
              await loadAttendanceData();
            } catch (error) {
              Alert.alert('Error', 'Manual check-out failed');
            }
          },
        },
      ]
    );
  };

  const getStatusColor = (status: string) => {
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

  const getStatusText = (status: string) => {
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

  const formatTime = (timeString?: string) => {
    if (!timeString) return '--:--';
    
    try {
      const date = new Date(timeString);
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
      });
    } catch {
      return timeString;
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Loading attendance data...</Text>
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
        <Text style={styles.headerTitle}>Attendance</Text>
        <TouchableOpacity
          style={styles.historyButton}
          onPress={() => navigation.navigate('AttendanceHistory')}
        >
          <Ionicons name="time-outline" size={24} color="#007AFF" />
        </TouchableOpacity>
      </View>

      {/* Today's Status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Today's Status</Text>
        
        <View style={styles.statusContainer}>
          <View style={styles.statusHeader}>
            <View
              style={[
                styles.statusIndicator,
                { backgroundColor: getStatusColor(todayAttendance.status) },
              ]}
            />
            <Text style={styles.statusText}>
              {getStatusText(todayAttendance.status)}
            </Text>
          </View>

          <View style={styles.timeContainer}>
            <View style={styles.timeItem}>
              <Text style={styles.timeLabel}>Check-in</Text>
              <Text style={styles.timeValue}>
                {formatTime(todayAttendance.check_in_time)}
              </Text>
            </View>
            
            <View style={styles.timeItem}>
              <Text style={styles.timeLabel}>Check-out</Text>
              <Text style={styles.timeValue}>
                {formatTime(todayAttendance.check_out_time)}
              </Text>
            </View>

            <View style={styles.timeItem}>
              <Text style={styles.timeLabel}>Total Hours</Text>
              <Text style={styles.timeValue}>
                {todayAttendance.total_hours || '--:--'}
              </Text>
            </View>
          </View>

          {todayAttendance.location && (
            <View style={styles.locationContainer}>
              <Ionicons name="location-outline" size={16} color="#666666" />
              <Text style={styles.locationText}>{todayAttendance.location}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Actions</Text>
        
        <View style={styles.actionButtons}>
          {todayAttendance.status === 'not_checked_in' && (
            <>
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#4ECDC4' }]}
                onPress={handleCheckIn}
              >
                <Ionicons name="camera-outline" size={24} color="#FFFFFF" />
                <Text style={styles.actionButtonText}>Face Check-in</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#66BB6A' }]}
                onPress={handleManualCheckIn}
              >
                <Ionicons name="log-in-outline" size={24} color="#FFFFFF" />
                <Text style={styles.actionButtonText}>Manual Check-in</Text>
              </TouchableOpacity>
            </>
          )}

          {todayAttendance.status === 'checked_in' && (
            <>
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#45B7D1' }]}
                onPress={handleCheckOut}
              >
                <Ionicons name="camera-outline" size={24} color="#FFFFFF" />
                <Text style={styles.actionButtonText}>Face Check-out</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#FFA726' }]}
                onPress={handleManualCheckOut}
              >
                <Ionicons name="log-out-outline" size={24} color="#FFFFFF" />
                <Text style={styles.actionButtonText}>Manual Check-out</Text>
              </TouchableOpacity>
            </>
          )}

          {todayAttendance.status === 'checked_out' && (
            <View style={styles.completedContainer}>
              <Ionicons name="checkmark-circle" size={48} color="#4ECDC4" />
              <Text style={styles.completedText}>Today's work completed</Text>
            </View>
          )}
        </View>
      </View>

      {/* This Week Stats */}
      {stats?.this_week && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>This Week</Text>
          <View style={styles.statsContainer}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.this_week.total_hours}</Text>
              <Text style={styles.statLabel}>Total Hours</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.this_week.days_present}</Text>
              <Text style={styles.statLabel}>Days Present</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.this_week.days_absent}</Text>
              <Text style={styles.statLabel}>Days Absent</Text>
            </View>
          </View>
        </View>
      )}

      {/* This Month Stats */}
      {stats?.this_month && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>This Month</Text>
          <View style={styles.statsContainer}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.this_month.total_hours}</Text>
              <Text style={styles.statLabel}>Total Hours</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.this_month.days_present}</Text>
              <Text style={styles.statLabel}>Days Present</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{stats.this_month.overtime_hours}</Text>
              <Text style={styles.statLabel}>Overtime</Text>
            </View>
          </View>
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
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333333',
  },
  historyButton: {
    padding: 8,
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
  statusContainer: {
    alignItems: 'center',
  },
  statusHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 8,
  },
  statusText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
  },
  timeContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    width: '100%',
    marginBottom: 15,
  },
  timeItem: {
    alignItems: 'center',
  },
  timeLabel: {
    fontSize: 12,
    color: '#666666',
    marginBottom: 4,
  },
  timeValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333333',
  },
  locationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
  },
  locationText: {
    fontSize: 14,
    color: '#666666',
    marginLeft: 4,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
  },
  actionButton: {
    flex: 1,
    margin: 5,
    padding: 15,
    borderRadius: 12,
    alignItems: 'center',
    minWidth: '45%',
  },
  actionButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 5,
    textAlign: 'center',
  },
  completedContainer: {
    alignItems: 'center',
    paddingVertical: 20,
    width: '100%',
  },
  completedText: {
    fontSize: 16,
    color: '#4ECDC4',
    fontWeight: '600',
    marginTop: 10,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  statLabel: {
    fontSize: 12,
    color: '#666666',
    marginTop: 4,
    textAlign: 'center',
  },
});
