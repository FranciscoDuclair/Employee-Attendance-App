# Face Recognition Setup Guide

## Overview

This guide covers the complete setup and usage of the face recognition system for the Employee Attendance Platform. The system uses advanced computer vision algorithms to verify employee identity during check-in and check-out processes.

## Prerequisites

### System Requirements
- Python 3.8+
- Django 5.2.5
- OpenCV 4.9.0+
- dlib 19.24.2+
- face-recognition 1.3.0+

### Hardware Requirements
- Camera-enabled mobile device
- Minimum 2GB RAM for face processing
- Good lighting conditions for optimal recognition

## Installation Steps

### 1. Install Dependencies

```bash
# Navigate to project directory
cd "f:\Employee Attendance APP"

# Activate virtual environment
venv\Scripts\activate

# Install new requirements
pip install -r requirements.txt
```

### 2. Run Database Migrations

```bash
# Create migrations for new models
python manage.py makemigrations attendance

# Apply migrations
python manage.py migrate
```

### 3. Initialize Face Recognition System

```bash
# Run setup command with default settings
python manage.py setup_face_recognition

# Or with custom settings
python manage.py setup_face_recognition \
    --confidence-threshold 0.7 \
    --enable-location \
    --office-lat 40.7128 \
    --office-lng -74.0060 \
    --location-radius 200 \
    --late-threshold 10
```

### 4. Create Superuser (if not exists)

```bash
python manage.py createsuperuser
```

### 5. Start Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

## Configuration

### Face Recognition Settings

Access Django Admin at `http://localhost:8000/admin/` and navigate to **Attendance Settings**:

- **Face Recognition Enabled**: Enable/disable face recognition system
- **Face Confidence Threshold**: Minimum confidence score (0.0-1.0)
- **Location Tracking**: Enable GPS-based attendance verification
- **Office Coordinates**: Set office location for proximity checking
- **Time Thresholds**: Configure late arrival and early departure rules

### API Endpoints

The system provides the following face recognition endpoints:

- `POST /api/attendance/face-setup/` - Initial face registration
- `POST /api/attendance/face-checkin/` - Face recognition check-in
- `POST /api/attendance/face-checkout/` - Face recognition check-out
- `GET /api/attendance/face-status/` - Check face recognition status
- `DELETE /api/attendance/face-remove/` - Remove face data

## Mobile App Setup

### 1. Install Dependencies

```bash
cd mobile_app
npm install
```

### 2. Update API Configuration

Edit `src/services/ApiService.ts` and update the API base URL:

```typescript
const API_BASE_URL = 'http://YOUR_SERVER_IP:8000/api';
```

### 3. Start Development Server

```bash
# For Expo
npm start

# For React Native CLI
npx react-native run-android
# or
npx react-native run-ios
```

## Usage Guide

### For Employees

#### 1. Initial Face Registration

1. Open the mobile app and log in
2. Navigate to **Profile** → **Face Recognition Setup**
3. Follow the on-screen instructions to capture your face
4. Ensure good lighting and position face within the guide frame
5. Wait for confirmation of successful setup

#### 2. Daily Check-in/Check-out

1. Open the mobile app
2. Tap **Check In** or **Check Out**
3. Select **Face Recognition** option
4. Position your face within the camera frame
5. Wait for verification and confirmation

#### 3. Troubleshooting Face Recognition

If face recognition fails:
- Ensure good lighting conditions
- Remove glasses or accessories if possible
- Keep face centered in the frame
- Try manual check-in as fallback

### For Administrators

#### 1. Monitor Face Recognition

Access Django Admin → **Attendance** to view:
- Face verification status for each attendance record
- Confidence scores for successful verifications
- Failed verification attempts

#### 2. Manage Settings

Adjust system parameters:
- Confidence threshold (higher = more strict)
- Location tracking requirements
- Manual attendance fallback options

#### 3. User Management

- View users without face recognition setup
- Reset face data if needed
- Monitor system usage and performance

## Security Considerations

### Data Protection
- Face encodings are stored as encrypted mathematical representations
- Original face images are not permanently stored
- All API communications use HTTPS in production

### Privacy Compliance
- Users can remove their face data at any time
- Face recognition is optional (manual check-in available)
- Data is stored locally and not shared with third parties

### Access Control
- Only authenticated users can access face recognition features
- Admin-only access to face recognition settings
- Audit trail for all face recognition activities

## Troubleshooting

### Common Issues

#### 1. Face Recognition Library Not Found
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install build-essential cmake
sudo apt-get install libopenblas-dev liblapack-dev
sudo apt-get install libx11-dev libgtk-3-dev

# Reinstall face-recognition
pip uninstall face-recognition dlib
pip install dlib
pip install face-recognition
```

#### 2. Poor Recognition Accuracy
- Increase confidence threshold in settings
- Ensure consistent lighting during setup and usage
- Re-register face data in different lighting conditions
- Check camera quality and focus

#### 3. Performance Issues
- Reduce image size in face recognition utils
- Use 'small' encoding model for faster processing
- Implement image caching for repeated verifications

#### 4. Database Migration Errors
```bash
# Reset migrations if needed
python manage.py migrate attendance zero
python manage.py makemigrations attendance
python manage.py migrate
```

### Log Files

Check log files for detailed error information:
- `logs/attendance.log` - General attendance system logs
- Django console output for real-time debugging

### Support Commands

```bash
# Check system status
python manage.py setup_face_recognition --reset

# Test face recognition utilities
python manage.py shell
>>> from utils.face_recognition_utils import FaceRecognitionUtils
>>> # Test face recognition functions

# View attendance statistics
python manage.py shell
>>> from attendance.models import Attendance
>>> Attendance.objects.filter(face_verified=True).count()
```

## Performance Optimization

### Server-side Optimizations
- Use Redis for caching face encodings
- Implement async processing for face verification
- Optimize image preprocessing pipeline

### Mobile App Optimizations
- Compress images before upload
- Implement local face detection before server verification
- Cache user face recognition status

## API Documentation

### Face Setup Endpoint

```http
POST /api/attendance/face-setup/
Content-Type: multipart/form-data

face_image: [image file]
```

**Response:**
```json
{
  "success": true,
  "message": "Face recognition setup successful",
  "confidence": 1.0
}
```

### Face Check-in Endpoint

```http
POST /api/attendance/face-checkin/
Content-Type: multipart/form-data

face_image: [image file]
latitude: 40.7128
longitude: -74.0060
location_accuracy: 10.0
notes: "Morning check-in"
```

**Response:**
```json
{
  "success": true,
  "message": "Face recognition check-in successful",
  "attendance": {
    "id": 123,
    "date": "2025-09-13",
    "check_in_time": "2025-09-13T09:00:00Z",
    "face_verified": true,
    "face_confidence": 0.95
  },
  "face_confidence": 0.95,
  "verification_message": "Face verification successful"
}
```

## Maintenance

### Regular Tasks
- Monitor face recognition accuracy rates
- Update confidence thresholds based on usage patterns
- Clean up old face images and logs
- Update dependencies and security patches

### Backup Procedures
- Backup user face encodings from database
- Export attendance settings configuration
- Maintain system configuration documentation

## Support

For technical support or questions:
1. Check this documentation first
2. Review log files for error details
3. Test with management commands
4. Contact system administrator

---

**Last Updated:** September 13, 2025
**Version:** 1.0.0
