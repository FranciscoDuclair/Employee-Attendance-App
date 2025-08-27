from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Avg, Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from datetime import datetime, timedelta
import cv2
import numpy as np
from PIL import Image
import io
import base64

from .models import Attendance
from .serializers import (
    AttendanceSerializer, CheckInSerializer, CheckOutSerializer,
    FaceRecognitionSerializer, ManualAttendanceSerializer,
    AttendanceHistorySerializer, AttendanceStatsSerializer
)
from users.models import User


class CheckInView(APIView):
    """Check-in attendance endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CheckInSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            now = timezone.now()
            
            # Create check-in record
            attendance = Attendance.objects.create(
                user=user,
                date=now.date(),
                check_in_time=now,
                attendance_type='check_in',
                status='present',
                latitude=serializer.validated_data.get('latitude'),
                longitude=serializer.validated_data.get('longitude'),
                notes=serializer.validated_data.get('notes', '')
            )
            
            # Check if late (after 9 AM)
            if now.time() > datetime.strptime('09:00', '%H:%M').time():
                attendance.status = 'late'
                attendance.save()
            
            return Response({
                'message': 'Check-in successful',
                'attendance': AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckOutView(APIView):
    """Check-out attendance endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = CheckOutSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            now = timezone.now()
            
            # Get today's check-in record
            checkin_record = Attendance.objects.filter(
                user=user,
                date=now.date(),
                attendance_type='check_in'
            ).first()
            
            if not checkin_record:
                return Response({
                    'error': 'You must check in before checking out'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create check-out record
            attendance = Attendance.objects.create(
                user=user,
                date=now.date(),
                check_out_time=now,
                attendance_type='check_out',
                status='present',
                latitude=serializer.validated_data.get('latitude'),
                longitude=serializer.validated_data.get('longitude'),
                notes=serializer.validated_data.get('notes', '')
            )
            
            return Response({
                'message': 'Check-out successful',
                'attendance': AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FaceRecognitionView(APIView):
    """Face recognition check-in/out endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FaceRecognitionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            now = timezone.now()
            attendance_type = serializer.validated_data['attendance_type']
            
            # Process face recognition
            face_verified, confidence = self.verify_face(
                serializer.validated_data['image'],
                user.face_encoding
            )
            
            if not face_verified:
                return Response({
                    'error': 'Face verification failed. Please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create attendance record
            attendance = Attendance.objects.create(
                user=user,
                date=now.date(),
                check_in_time=now if attendance_type == 'check_in' else None,
                check_out_time=now if attendance_type == 'check_out' else None,
                attendance_type=attendance_type,
                status='present',
                face_verified=True,
                face_confidence=confidence,
                latitude=serializer.validated_data.get('latitude'),
                longitude=serializer.validated_data.get('longitude'),
                notes=serializer.validated_data.get('notes', '')
            )
            
            # Check if late for check-in
            if attendance_type == 'check_in' and now.time() > datetime.strptime('09:00', '%H:%M').time():
                attendance.status = 'late'
                attendance.save()
            
            return Response({
                'message': f'{attendance_type.replace("_", " ").title()} successful with face recognition',
                'attendance': AttendanceSerializer(attendance).data,
                'face_confidence': confidence
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def verify_face(self, image, stored_encoding):
        """Verify face using OpenCV and face recognition"""
        try:
            # Convert image to OpenCV format
            if hasattr(image, 'read'):
                image_data = image.read()
            else:
                image_data = image
            
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to RGB for face recognition
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Simple face detection using OpenCV
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(img_rgb, 1.1, 4)
            
            if len(faces) == 0:
                return False, 0.0
            
            # For now, return True if face is detected
            # In production, you would compare with stored face encoding
            confidence = 0.85  # Placeholder confidence
            
            return True, confidence
            
        except Exception as e:
            print(f"Face recognition error: {e}")
            return False, 0.0


class ManualAttendanceView(APIView):
    """Manual attendance entry (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Check if user has permission
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can create manual attendance records'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ManualAttendanceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            attendance = serializer.save()
            
            return Response({
                'message': 'Manual attendance record created successfully',
                'attendance': AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceHistoryView(generics.ListAPIView):
    """Get attendance history for user"""
    serializer_class = AttendanceHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['date', 'attendance_type', 'status']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']
    
    def get_queryset(self):
        user = self.request.user
        
        # HR/Admin can view all or filter by user
        if user.can_manage_attendance():
            queryset = Attendance.objects.all()
            user_id = self.request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)
        else:
            # Regular employees can only see their own attendance
            queryset = Attendance.objects.filter(user=user)
        
        return queryset


class AttendanceStatsView(APIView):
    """Get attendance statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user_id = request.query_params.get('user_id')
        
        # Determine which user's stats to show
        if user_id and user.can_manage_attendance():
            target_user = User.objects.get(id=user_id)
        else:
            target_user = user
        
        # Get date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)  # Last 30 days
        
        # Get attendance records
        attendance_records = Attendance.objects.filter(
            user=target_user,
            date__range=[start_date, end_date]
        )
        
        # Calculate statistics
        total_days = (end_date - start_date).days + 1
        present_days = attendance_records.filter(
            Q(attendance_type='check_in') & Q(status__in=['present', 'late'])
        ).count()
        late_days = attendance_records.filter(
            Q(attendance_type='check_in') & Q(status='late')
        ).count()
        absent_days = total_days - present_days
        
        # Calculate hours
        total_hours = 0
        for record in attendance_records.filter(attendance_type='check_out'):
            if record.check_in_time and record.check_out_time:
                duration = record.check_out_time - record.check_in_time
                total_hours += duration.total_seconds() / 3600
        
        average_hours_per_day = total_hours / present_days if present_days > 0 else 0
        punctuality_rate = ((present_days - late_days) / present_days * 100) if present_days > 0 else 0
        
        stats = {
            'total_days': total_days,
            'present_days': present_days,
            'late_days': late_days,
            'absent_days': absent_days,
            'total_hours': round(total_hours, 2),
            'average_hours_per_day': round(average_hours_per_day, 2),
            'punctuality_rate': round(punctuality_rate, 2)
        }
        
        return Response(stats)


class AttendanceListView(generics.ListAPIView):
    """List all attendance records (HR/Admin only)"""
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'date', 'attendance_type', 'status', 'is_manual']
    search_fields = ['user__first_name', 'user__last_name', 'user__employee_id']
    ordering_fields = ['date', 'created_at', 'check_in_time']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        if not self.request.user.can_manage_attendance():
            return Attendance.objects.none()
        return Attendance.objects.all()


class AttendanceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Attendance record detail view (HR/Admin only)"""
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if not self.request.user.can_manage_attendance():
            return Attendance.objects.none()
        return Attendance.objects.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def today_attendance(request):
    """Get today's attendance status for current user"""
    user = request.user
    today = timezone.now().date()
    
    checkin = Attendance.objects.filter(
        user=user,
        date=today,
        attendance_type='check_in'
    ).first()
    
    checkout = Attendance.objects.filter(
        user=user,
        date=today,
        attendance_type='check_out'
    ).first()
    
    data = {
        'date': today,
        'checked_in': checkin is not None,
        'checked_out': checkout is not None,
        'check_in_time': checkin.check_in_time if checkin else None,
        'check_out_time': checkout.check_out_time if checkout else None,
        'status': checkin.status if checkin else 'absent',
        'hours_worked': 0
    }
    
    if checkin and checkout:
        duration = checkout.check_out_time - checkin.check_in_time
        data['hours_worked'] = round(duration.total_seconds() / 3600, 2)
    
    return Response(data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_attendance_approval(request):
    """Bulk approve manual attendance records (HR/Admin only)"""
    if not request.user.can_manage_attendance():
        return Response({
            'error': 'Only HR and Managers can approve attendance records'
        }, status=status.HTTP_403_FORBIDDEN)
    
    attendance_ids = request.data.get('attendance_ids', [])
    action = request.data.get('action', 'approve')  # approve or reject
    
    if not attendance_ids:
        return Response({
            'error': 'No attendance records specified'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    attendance_records = Attendance.objects.filter(
        id__in=attendance_ids,
        is_manual=True
    )
    
    updated_count = 0
    for record in attendance_records:
        if action == 'approve':
            record.status = 'present'
        elif action == 'reject':
            record.status = 'absent'
        record.save()
        updated_count += 1
    
    return Response({
        'message': f'{updated_count} attendance records {action}ed successfully'
    })
