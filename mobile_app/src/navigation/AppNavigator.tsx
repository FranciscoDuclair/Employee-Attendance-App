import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useAuth } from '../contexts/AuthContext';

// Import screens
import LoginScreen from '../screens/auth/LoginScreen';
import LoadingScreen from '../screens/LoadingScreen';
import DashboardScreen from '../screens/dashboard/DashboardScreen';
import AttendanceScreen from '../screens/attendance/AttendanceScreen';
import FaceRecognitionScreen from '../screens/attendance/FaceRecognitionScreen';
import AttendanceHistoryScreen from '../screens/attendance/AttendanceHistoryScreen';
import LeaveScreen from '../screens/leave/LeaveScreen';
import LeaveRequestScreen from '../screens/leave/LeaveRequestScreen';
import LeaveHistoryScreen from '../screens/leave/LeaveHistoryScreen';
import ShiftScreen from '../screens/shift/ShiftScreen';
import ShiftCalendarScreen from '../screens/shift/ShiftCalendarScreen';
import PayrollScreen from '../screens/payroll/PayrollScreen';
import NotificationsScreen from '../screens/notifications/NotificationsScreen';
import ProfileScreen from '../screens/profile/ProfileScreen';
import SettingsScreen from '../screens/settings/SettingsScreen';

// Import icons
import { Ionicons } from '@expo/vector-icons';

export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
  FaceRecognition: {
    mode: 'checkin' | 'checkout' | 'setup';
  };
  LeaveRequest: {
    leaveType?: number;
  };
  AttendanceHistory: undefined;
  LeaveHistory: undefined;
  ShiftCalendar: undefined;
  Notifications: undefined;
  Settings: undefined;
};

export type MainTabParamList = {
  Dashboard: undefined;
  Attendance: undefined;
  Leave: undefined;
  Shift: undefined;
  Payroll: undefined;
  Profile: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<MainTabParamList>();

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap;

          switch (route.name) {
            case 'Dashboard':
              iconName = focused ? 'home' : 'home-outline';
              break;
            case 'Attendance':
              iconName = focused ? 'time' : 'time-outline';
              break;
            case 'Leave':
              iconName = focused ? 'calendar' : 'calendar-outline';
              break;
            case 'Shift':
              iconName = focused ? 'people' : 'people-outline';
              break;
            case 'Payroll':
              iconName = focused ? 'card' : 'card-outline';
              break;
            case 'Profile':
              iconName = focused ? 'person' : 'person-outline';
              break;
            default:
              iconName = 'help-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#007AFF',
        tabBarInactiveTintColor: 'gray',
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#FFFFFF',
          borderTopWidth: 1,
          borderTopColor: '#E0E0E0',
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
      })}
    >
      <Tab.Screen 
        name="Dashboard" 
        component={DashboardScreen}
        options={{ title: 'Home' }}
      />
      <Tab.Screen 
        name="Attendance" 
        component={AttendanceScreen}
        options={{ title: 'Attendance' }}
      />
      <Tab.Screen 
        name="Leave" 
        component={LeaveScreen}
        options={{ title: 'Leave' }}
      />
      <Tab.Screen 
        name="Shift" 
        component={ShiftScreen}
        options={{ title: 'Schedule' }}
      />
      <Tab.Screen 
        name="Payroll" 
        component={PayrollScreen}
        options={{ title: 'Payroll' }}
      />
      <Tab.Screen 
        name="Profile" 
        component={ProfileScreen}
        options={{ title: 'Profile' }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          animation: 'slide_from_right',
        }}
      >
        {user ? (
          // Authenticated screens
          <>
            <Stack.Screen name="Main" component={MainTabs} />
            <Stack.Screen 
              name="FaceRecognition" 
              component={FaceRecognitionScreen}
              options={{
                headerShown: true,
                title: 'Face Recognition',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="LeaveRequest" 
              component={LeaveRequestScreen}
              options={{
                headerShown: true,
                title: 'Request Leave',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="AttendanceHistory" 
              component={AttendanceHistoryScreen}
              options={{
                headerShown: true,
                title: 'Attendance History',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="LeaveHistory" 
              component={LeaveHistoryScreen}
              options={{
                headerShown: true,
                title: 'Leave History',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="ShiftCalendar" 
              component={ShiftCalendarScreen}
              options={{
                headerShown: true,
                title: 'Shift Calendar',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="Notifications" 
              component={NotificationsScreen}
              options={{
                headerShown: true,
                title: 'Notifications',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
            <Stack.Screen 
              name="Settings" 
              component={SettingsScreen}
              options={{
                headerShown: true,
                title: 'Settings',
                headerStyle: {
                  backgroundColor: '#007AFF',
                },
                headerTintColor: '#FFFFFF',
                headerTitleStyle: {
                  fontWeight: 'bold',
                },
              }}
            />
          </>
        ) : (
          // Authentication screens
          <Stack.Screen name="Auth" component={LoginScreen} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

