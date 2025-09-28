import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export default function AttendanceHistoryScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Attendance History</Text>
      <Text style={styles.subtitle}>View your attendance records</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    paddingHorizontal: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
  },
});
