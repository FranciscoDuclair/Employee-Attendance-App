# Attendance System API Documentation

## Overview

The Attendance System provides comprehensive tracking of employee check-ins, check-outs, and attendance management with support for face recognition, manual entries, and detailed reporting.

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### 1. Check-In Attendance

**POST** `/api/attendance/check-in/`

Check in for the current day.

**Request Body:**
```json
{
  "latitude": "40.7128",
  "longitude": "-74.0060",
  "notes": "Arrived at work"
}
```

**Response:**
```json
{
  "message": "Check-in successful",
  "attendance": {
    "id": 1,
    "user": 1,
    "user_name": "John Doe",
    "employee_id": "EMP001",
    "date": "2025-08-26",
    "check_in_time": "2025-08-26T09:00:00Z",
    "check_out_time": null,
    "attendance_type": "check_in",
    "status": "present",
    "face_verified": false,
    "face_confidence": null,
    "is_manual": false,
    "manual_approved_by": null,
    "manual_reason": "",
    "latitude": "40.7128",
    "longitude": "-74.0060",
    "notes": "Arrived at work",
    "hours_worked": 0,
    "is_late": false,
    "created_at": "2025-08-26T09:00:00Z",
    "updated_at": "2025-08-26T09:00:00Z"
  }
}
```

**Notes:**
- Automatically detects late arrival (after 9:00 AM)
- Prevents duplicate check-ins for the same day
- Optional location tracking and notes

### 2. Check-Out Attendance

**POST** `/api/attendance/check-out/`

Check out for the current day.

**Request Body:**
```json
{
  "latitude": "40.7128",
  "longitude": "-74.0060",
  "notes": "Leaving work"
}
```

**Response:**
```json
{
  "message": "Check-out successful",
  "attendance": {
    "id": 2,
    "user": 1,
    "user_name": "John Doe",
    "employee_id": "EMP001",
    "date": "2025-08-26",
    "check_in_time": null,
    "check_out_time": "2025-08-26T17:00:00Z",
    "attendance_type": "check_out",
    "status": "present",
    "face_verified": false,
    "face_confidence": null,
    "is_manual": false,
    "manual_approved_by": null,
    "manual_reason": "",
    "latitude": "40.7128",
    "longitude": "-74.0060",
    "notes": "Leaving work",
    "hours_worked": 0,
    "is_late": false,
    "created_at": "2025-08-26T17:00:00Z",
    "updated_at": "2025-08-26T17:00:00Z"
  }
}
```

**Notes:**
- Requires prior check-in for the same day
- Prevents duplicate check-outs
- Calculates hours worked when both check-in and check-out exist

### 3. Face Recognition Attendance

**POST** `/api/attendance/face-recognition/`

Check in/out using face recognition technology.

**Request Body:**
```json
{
  "image": "base64_encoded_image_or_file",
  "attendance_type": "check_in",
  "latitude": "40.7128",
  "longitude": "-74.0060",
  "notes": "Face recognition check-in"
}
```

**Response:**
```json
{
  "message": "Check in successful with face recognition",
  "attendance": {
    "id": 3,
    "user": 1,
    "user_name": "John Doe",
    "employee_id": "EMP001",
    "date": "2025-08-26",
    "check_in_time": "2025-08-26T09:00:00Z",
    "check_out_time": null,
    "attendance_type": "check_in",
    "status": "present",
    "face_verified": true,
    "face_confidence": 0.85,
    "is_manual": false,
    "manual_approved_by": null,
    "manual_reason": "",
    "latitude": "40.7128",
    "longitude": "-74.0060",
    "notes": "Face recognition check-in",
    "hours_worked": 0,
    "is_late": false,
    "created_at": "2025-08-26T09:00:00Z",
    "updated_at": "2025-08-26T09:00:00Z"
  },
  "face_confidence": 0.85
}
```

**Notes:**
- Supports both check-in and check-out
- Uses OpenCV for face detection
- Returns confidence score
- Automatically detects late arrivals

### 4. Manual Attendance Entry

**POST** `/api/attendance/manual/`

Create manual attendance records (HR/Admin only).

**Request Body:**
```json
{
  "user": 1,
  "date": "2025-08-26",
  "check_in_time": "2025-08-26T09:00:00Z",
  "check_out_time": "2025-08-26T17:00:00Z",
  "attendance_type": "check_in",
  "status": "present",
  "notes": "Manual entry for missed check-in"
}
```

**Response:**
```json
{
  "message": "Manual attendance record created successfully",
  "attendance": {
    "id": 4,
    "user": 1,
    "user_name": "John Doe",
    "employee_id": "EMP001",
    "date": "2025-08-26",
    "check_in_time": "2025-08-26T09:00:00Z",
    "check_out_time": "2025-08-26T17:00:00Z",
    "attendance_type": "check_in",
    "status": "present",
    "face_verified": false,
    "face_confidence": null,
    "is_manual": true,
    "manual_approved_by": 2,
    "manual_reason": "HR approved",
    "latitude": null,
    "longitude": null,
    "notes": "Manual entry for missed check-in",
    "hours_worked": 8.0,
    "is_late": false,
    "created_at": "2025-08-26T10:00:00Z",
    "updated_at": "2025-08-26T10:00:00Z"
  }
}
```

**Notes:**
- Only HR and Managers can create manual records
- Automatically marks as manual entry
- Records who approved the manual entry

### 5. Attendance History

**GET** `/api/attendance/history/`

Get attendance history for the authenticated user or filtered by user (HR/Admin).

**Query Parameters:**
- `user_id`: Filter by specific user (HR/Admin only)
- `date`: Filter by specific date
- `attendance_type`: Filter by type (check_in, check_out)
- `status`: Filter by status (present, late, absent, half_day)
- `ordering`: Order by field (date, created_at)

**Response:**
```json
{
  "count": 30,
  "next": "http://localhost:8000/api/attendance/history/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user_name": "John Doe",
      "employee_id": "EMP001",
      "date": "2025-08-26",
      "check_in_time": "2025-08-26T09:00:00Z",
      "check_out_time": "2025-08-26T17:00:00Z",
      "attendance_type": "check_in",
      "status": "present",
      "face_verified": false,
      "is_manual": false,
      "hours_worked": 8.0,
      "is_late": false,
      "notes": ""
    }
  ]
}
```

### 6. Attendance Statistics

**GET** `/api/attendance/stats/`

Get attendance statistics for the last 30 days.

**Query Parameters:**
- `user_id`: Get stats for specific user (HR/Admin only)

**Response:**
```json
{
  "total_days": 30,
  "present_days": 22,
  "late_days": 3,
  "absent_days": 8,
  "total_hours": 176.0,
  "average_hours_per_day": 8.0,
  "punctuality_rate": 86.36
}
```

### 7. Today's Attendance Status

**GET** `/api/attendance/today/`

Get current day's attendance status for the authenticated user.

**Response:**
```json
{
  "date": "2025-08-26",
  "checked_in": true,
  "checked_out": false,
  "check_in_time": "2025-08-26T09:00:00Z",
  "check_out_time": null,
  "status": "present",
  "hours_worked": 0
}
```

### 8. Attendance List (HR/Admin Only)

**GET** `/api/attendance/list/`

List all attendance records with filtering and search capabilities.

**Query Parameters:**
- `user`: Filter by user ID
- `date`: Filter by date
- `attendance_type`: Filter by type
- `status`: Filter by status
- `is_manual`: Filter by manual entries
- `search`: Search by user name, employee ID, or email
- `ordering`: Order by field

**Response:**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/attendance/list/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 1,
      "user_name": "John Doe",
      "employee_id": "EMP001",
      "date": "2025-08-26",
      "check_in_time": "2025-08-26T09:00:00Z",
      "check_out_time": null,
      "attendance_type": "check_in",
      "status": "present",
      "face_verified": false,
      "face_confidence": null,
      "is_manual": false,
      "manual_approved_by": null,
      "manual_reason": "",
      "latitude": "40.7128",
      "longitude": "-74.0060",
      "notes": "Arrived at work",
      "hours_worked": 0,
      "is_late": false,
      "created_at": "2025-08-26T09:00:00Z",
      "updated_at": "2025-08-26T09:00:00Z"
    }
  ]
}
```

### 9. Attendance Detail (HR/Admin Only)

**GET** `/api/attendance/{id}/`

Get detailed information about a specific attendance record.

**Response:** Same as individual attendance object above.

**PUT** `/api/attendance/{id}/`

Update attendance record details.

**DELETE** `/api/attendance/{id}/`

Delete attendance record.

### 10. Bulk Attendance Approval (HR/Admin Only)

**POST** `/api/attendance/bulk-approval/`

Approve or reject multiple manual attendance records.

**Request Body:**
```json
{
  "attendance_ids": [1, 2, 3, 4],
  "action": "approve"
}
```

**Response:**
```json
{
  "message": "4 attendance records approved successfully"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "You must check in before checking out"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "error": "Only HR and Managers can create manual attendance records"
}
```

### 404 Not Found
```json
{
  "error": "Attendance record not found"
}
```

## Face Recognition Implementation

The face recognition system uses:
- **OpenCV** for image processing and face detection
- **Haar Cascade Classifier** for face detection
- **Confidence scoring** for verification quality
- **Base64 or file upload** for image input

### Face Recognition Process:
1. Image is uploaded via API
2. OpenCV processes the image
3. Face detection is performed
4. Confidence score is calculated
5. Attendance record is created if verification passes

## Location Tracking

Optional GPS coordinates can be included with attendance records:
- **Latitude**: Decimal degrees (-90 to 90)
- **Longitude**: Decimal degrees (-180 to 180)
- Useful for verifying attendance location
- Can be used for geofencing applications

## Status Values

- **present**: On time arrival
- **late**: Arrived after 9:00 AM
- **absent**: No attendance record
- **half_day**: Partial attendance

## Permissions

### Employee Role
- Can check in/out
- Can use face recognition
- Can view own history and stats
- Cannot create manual entries

### Manager Role
- All Employee permissions
- Can view team attendance
- Can create manual entries for team
- Can approve/reject attendance

### HR/Admin Role
- All Manager permissions
- Can view all attendance records
- Can create manual entries for anyone
- Can bulk approve/reject records
- Full attendance management access

## Example Usage

### Check-in with location
```bash
curl -X POST http://localhost:8000/api/attendance/check-in/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": "40.7128",
    "longitude": "-74.0060",
    "notes": "Arrived at office"
  }'
```

### Get attendance history
```bash
curl -X GET "http://localhost:8000/api/attendance/history/?date=2025-08-26" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create manual attendance (HR only)
```bash
curl -X POST http://localhost:8000/api/attendance/manual/ \
  -H "Authorization: Bearer HR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user": 1,
    "date": "2025-08-26",
    "check_in_time": "2025-08-26T09:00:00Z",
    "attendance_type": "check_in",
    "status": "present",
    "notes": "HR approved manual entry"
  }'
```

## Testing

Run attendance tests with:
```bash
python manage.py test attendance
```

## Notes

- All timestamps are in UTC
- Face recognition requires proper image quality
- Location tracking is optional but recommended
- Manual entries are automatically flagged for audit
- Bulk operations are available for HR/Admin users
- Real-time notifications can be integrated for attendance events
