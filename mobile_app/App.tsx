import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { Provider as PaperProvider } from 'react-native-paper';
import { Provider as ReduxProvider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from './src/contexts/AuthContext';
import { NotificationProvider } from './src/contexts/NotificationContext';
import AppNavigator from './src/navigation/AppNavigator';
import LoadingScreen from './src/screens/LoadingScreen';
import { store, persistor } from './src/store/store';

const theme = {
  colors: {
    primary: '#007AFF',
    accent: '#FF6B6B',
    background: '#FFFFFF',
    surface: '#F8F9FA',
    text: '#333333',
    disabled: '#CCCCCC',
    placeholder: '#999999',
    backdrop: 'rgba(0, 0, 0, 0.5)',
  },
};

export default function App() {
  return (
    <SafeAreaProvider>
      <ReduxProvider store={store}>
        <PersistGate loading={<LoadingScreen />} persistor={persistor}>
          <PaperProvider theme={theme}>
            <AuthProvider>
              <NotificationProvider>
                <AppNavigator />
                <StatusBar style="auto" />
              </NotificationProvider>
            </AuthProvider>
          </PaperProvider>
        </PersistGate>
      </ReduxProvider>
    </SafeAreaProvider>
  );
}