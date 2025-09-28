import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { Camera, CameraType } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import ApiService from '../../services/ApiService';

const { width, height } = Dimensions.get('window');

interface RouteParams {
  mode: 'checkin' | 'checkout' | 'setup';
}

export default function FaceRecognitionScreen() {
  const navigation = useNavigation();
  const route = useRoute();
  const { mode } = route.params as RouteParams;
  
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [type, setType] = useState(CameraType.front);
  const [isProcessing, setIsProcessing] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const cameraRef = useRef<Camera>(null);

  useEffect(() => {
    requestCameraPermission();
  }, []);

  const requestCameraPermission = async () => {
    const { status } = await Camera.requestCameraPermissionsAsync();
    setHasPermission(status === 'granted');
  };

  const startCountdown = () => {
    setCountdown(3);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          capturePhoto();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const capturePhoto = async () => {
    if (!cameraRef.current || isProcessing) return;

    setIsProcessing(true);

    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.8,
        base64: true,
        skipProcessing: false,
      });

      await processAttendance(photo);
    } catch (error) {
      console.error('Error capturing photo:', error);
      Alert.alert('Error', 'Failed to capture photo. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const processAttendance = async (photo: any) => {
    try {
      const formData = new FormData();
      formData.append('face_image', {
        uri: photo.uri,
        type: 'image/jpeg',
        name: 'attendance_photo.jpg',
      } as any);

      let response;
      if (mode === 'checkin') {
        response = await ApiService.checkIn(formData);
      } else if (mode === 'checkout') {
        response = await ApiService.checkOut(formData);
      } else {
        // Setup mode - register face
        response = await ApiService.setupFaceRecognition(formData);
      }

      if (response.success) {
        Alert.alert(
          'Success',
          mode === 'setup' 
            ? 'Face recognition setup completed successfully!'
            : `${mode === 'checkin' ? 'Check-in' : 'Check-out'} successful!`,
          [
            {
              text: 'OK',
              onPress: () => navigation.goBack(),
            },
          ]
        );
      } else {
        throw new Error(response.message || 'Face recognition failed');
      }
    } catch (error: any) {
      console.error('Attendance processing error:', error);
      
      let errorMessage = 'Failed to process attendance. Please try again.';
      if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }

      Alert.alert('Error', errorMessage);
    }
  };

  const flipCamera = () => {
    setType(type === CameraType.back ? CameraType.front : CameraType.back);
  };

  if (hasPermission === null) {
    return (
      <View style={styles.permissionContainer}>
        <Text>Requesting camera permission...</Text>
      </View>
    );
  }

  if (hasPermission === false) {
    return (
      <View style={styles.permissionContainer}>
        <Ionicons name="camera-outline" size={64} color="#999999" />
        <Text style={styles.permissionText}>
          Camera permission is required for face recognition
        </Text>
        <TouchableOpacity
          style={styles.permissionButton}
          onPress={requestCameraPermission}
        >
          <Text style={styles.permissionButtonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Camera
        ref={cameraRef}
        style={styles.camera}
        type={type}
        ratio="16:9"
      >
        {/* Overlay */}
        <View style={styles.overlay}>
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity
              style={styles.headerButton}
              onPress={() => navigation.goBack()}
            >
              <Ionicons name="close" size={24} color="#FFFFFF" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>
              {mode === 'setup' 
                ? 'Setup Face Recognition'
                : mode === 'checkin' 
                ? 'Check In' 
                : 'Check Out'
              }
            </Text>
            <TouchableOpacity
              style={styles.headerButton}
              onPress={flipCamera}
            >
              <Ionicons name="camera-reverse" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>

          {/* Face guide */}
          <View style={styles.faceGuideContainer}>
            <View style={styles.faceGuide}>
              <View style={styles.faceGuideCorner} style={[styles.topLeft]} />
              <View style={styles.faceGuideCorner} style={[styles.topRight]} />
              <View style={styles.faceGuideCorner} style={[styles.bottomLeft]} />
              <View style={styles.faceGuideCorner} style={[styles.bottomRight]} />
            </View>
            
            {countdown > 0 && (
              <View style={styles.countdownContainer}>
                <Text style={styles.countdownText}>{countdown}</Text>
              </View>
            )}
          </View>

          {/* Instructions */}
          <View style={styles.instructions}>
            <Text style={styles.instructionText}>
              {countdown > 0 
                ? 'Get ready...'
                : isProcessing
                ? 'Processing...'
                : 'Position your face within the frame and tap capture'
              }
            </Text>
          </View>

          {/* Controls */}
          <View style={styles.controls}>
            {!isProcessing && countdown === 0 && (
              <TouchableOpacity
                style={styles.captureButton}
                onPress={startCountdown}
              >
                <View style={styles.captureButtonInner} />
              </TouchableOpacity>
            )}
            
            {isProcessing && (
              <View style={styles.processingContainer}>
                <ActivityIndicator size="large" color="#FFFFFF" />
              </View>
            )}
          </View>
        </View>
      </Camera>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
  },
  permissionText: {
    fontSize: 16,
    color: '#666666',
    textAlign: 'center',
    marginVertical: 20,
  },
  permissionButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  permissionButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  camera: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 20,
  },
  headerButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  faceGuideContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  faceGuide: {
    width: 250,
    height: 300,
    position: 'relative',
  },
  faceGuideCorner: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderColor: '#FFFFFF',
    borderWidth: 3,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderBottomWidth: 0,
    borderRightWidth: 0,
  },
  topRight: {
    top: 0,
    right: 0,
    borderBottomWidth: 0,
    borderLeftWidth: 0,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderTopWidth: 0,
    borderRightWidth: 0,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderTopWidth: 0,
    borderLeftWidth: 0,
  },
  countdownContainer: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  countdownText: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  instructions: {
    paddingHorizontal: 20,
    paddingVertical: 20,
    alignItems: 'center',
  },
  instructionText: {
    fontSize: 16,
    color: '#FFFFFF',
    textAlign: 'center',
  },
  controls: {
    paddingBottom: 50,
    alignItems: 'center',
  },
  captureButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: '#FFFFFF',
  },
  captureButtonInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#FFFFFF',
  },
  processingContainer: {
    width: 80,
    height: 80,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
