from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q
from datetime import date, datetime, timedelta
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters
import logging

from .models import Attendance, AttendanceSettings
from .serializers import AttendanceSerializer, AttendanceCreateSerializer
from users.models import User
from utils.face_recognition_utils import FaceRecognitionUtils, FaceRecognitionError

logger = logging.getLogger(__name__)


class AttendanceListView(generics.ListAPIView):
    """List attendance records"""
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter] if DjangoFilterBackend else [filters.OrderingFilter]
    filterset_fields = ['status', 'attendance_type', 'date'] if DjangoFilterBackend else []
    ordering_fields = ['date', 'created_at']
    ordering = ['-date', '-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['hr', 'manager']:
            # HR and managers can see all records
            return Attendance.objects.all()
        else:
            # Employees can only see their own records
            return Attendance.objects.filter(user=user)


class CheckInView(APIView):
    """Employee check-in endpoint with face verification"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        today = date.today()
        now = timezone.now()
        
        # Check if user already checked in today
        existing_checkin = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type='check_in'
        ).first()
        
        if existing_checkin:
            return Response(
                {'error': 'You have already checked in today.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Face recognition is mandatory for all check-ins
        if not user.face_encoding:
            return Response(
                {
                    'error': 'Face recognition setup is required.',
                    'detail': 'Please set up your face recognition profile before checking in.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Face image is required
        face_image = request.FILES.get('face_image')
        if not face_image:
            return Response(
                {
                    'error': 'Face image is required',
                    'detail': 'Please capture your face to verify your identity.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Process the uploaded face image
            face_utils = FaceRecognitionUtils()
            image_array = face_utils.preprocess_image(face_image)
            
            # Verify face against user's stored encoding
            match, confidence = face_utils.compare_faces(
                user.face_encoding,
                image_array
            )
            
            settings = AttendanceSettings.get_settings()
            confidence_threshold = settings.face_confidence_threshold * 100
            
            if not match or confidence < confidence_threshold:
                logger.warning(f"Face verification failed for user {user.email} (Confidence: {confidence:.2f}%, Threshold: {confidence_threshold:.2f}%)")
                return Response(
                    {
                        'error': 'Face verification failed',
                        'detail': 'Your face was not recognized. Please ensure good lighting and try again.',
                        'confidence': f"{confidence:.2f}%",
                        'threshold': f"{confidence_threshold:.2f}%"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            face_verified = True
            face_confidence = confidence / 100  # Convert to 0-1 scale
            
            # Save the face image for audit
            filename = f"checkin_{user.id}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
            face_image.name = filename
            
        except FaceRecognitionError as e:
            logger.error(f"Face recognition error during check-in: {str(e)}")
            return Response(
                {
                    'error': 'Face verification error',
                    'detail': 'An error occurred while processing your face. Please try again.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during face verification: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'Verification failed',
                    'detail': 'An unexpected error occurred. Please try again or contact support.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Face verification is already handled above for face_recognition_enabled
        
        # Create check-in record
        data = request.data.copy()
        data['user'] = user.id
        data['attendance_type'] = 'check_in'
        data['check_in_time'] = now
        data['date'] = today
        data['face_verified'] = face_verified
        data['face_confidence'] = face_confidence
        
        if settings.face_recognition_enabled and face_image:
            data['face_image'] = face_image
        
        serializer = AttendanceCreateSerializer(data=data)
        if serializer.is_valid():
            attendance = serializer.save()
            
            # Log the successful check-in
            logger.info(f"User {user.email} checked in successfully with {face_confidence*100:.2f}% confidence")
            
            return Response({
                'message': 'Checked in successfully',
                'face_verified': face_verified,
                'face_confidence': face_confidence,
                'attendance': AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckOutView(APIView):
    """Employee check-out endpoint with face verification"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        today = date.today()
        now = timezone.now()
        
        # Find today's check-in record
        checkin_record = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type='check_in'
        ).first()
        
        # Check if already checked out
        existing_checkout = Attendance.objects.filter(
            user=user,
            date=today,
            attendance_type='check_out'
        ).exists()
        
        if existing_checkout:
            return Response(
                {'error': 'You have already checked out today.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Face recognition is mandatory for all check-outs
        if not user.face_encoding:
            return Response(
                {
                    'error': 'Face recognition setup is required.',
                    'detail': 'Please set up your face recognition profile before checking out.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Face image is required
        face_image = request.FILES.get('face_image')
        if not face_image:
            return Response(
                {
                    'error': 'Face image is required',
                    'detail': 'Please capture your face to verify your identity.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Process the uploaded face image
            face_utils = FaceRecognitionUtils()
            image_array = face_utils.preprocess_image(face_image)
            
            # Verify face against user's stored encoding
            match, confidence = face_utils.compare_faces(
                user.face_encoding,
                image_array
            )
            
            settings = AttendanceSettings.get_settings()
            confidence_threshold = settings.face_confidence_threshold * 100
            
            if not match or confidence < confidence_threshold:
                logger.warning(f"Face verification failed for user {user.email} during check-out (Confidence: {confidence:.2f}%, Threshold: {confidence_threshold:.2f}%)")
                return Response(
                    {
                        'error': 'Face verification failed',
                        'detail': 'Your face was not recognized. Please ensure good lighting and try again.',
                        'confidence': f"{confidence:.2f}%",
                        'threshold': f"{confidence_threshold:.2f}%"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            face_verified = True
            face_confidence = confidence / 100  # Convert to 0-1 scale
            
            # Save the face image for audit
            filename = f"checkout_{user.id}_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
            face_image.name = filename
            
        except FaceRecognitionError as e:
            logger.error(f"Face recognition error during check-out: {str(e)}")
            return Response(
                {
                    'error': 'Face verification error',
                    'detail': 'An error occurred while processing your face. Please try again.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during face verification: {str(e)}", exc_info=True)
            return Response(
                {
                    'error': 'Verification failed',
                    'detail': 'An unexpected error occurred. Please try again or contact support.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Create check-out record
        data = request.data.copy()
        data['user'] = user.id
        data['attendance_type'] = 'check_out'
        data['check_out_time'] = now
        data['date'] = today
        data['face_verified'] = face_verified
        data['face_confidence'] = face_confidence
        
        if settings.face_recognition_enabled and face_image:
            data['face_image'] = face_image
        
        # Calculate hours worked if check-in time is available
        if checkin_record.check_in_time:
            time_worked = (now - checkin_record.check_in_time).total_seconds() / 3600
            data['hours_worked'] = round(time_worked, 2)
        
        serializer = AttendanceCreateSerializer(data=data)
        if serializer.is_valid():
            attendance = serializer.save()
            
            # Log the successful check-out
            logger.info(f"User {user.email} checked out successfully with {face_confidence*100:.2f}% confidence")
            
            return Response({
                'message': 'Checked out successfully',
                'face_verified': face_verified,
                'face_confidence': face_confidence,
                'hours_worked': data.get('hours_worked'),
                'attendance': AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def today_attendance(request):
    """Get today's attendance record for current user"""
    user = request.user
    today = date.today()
    
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
    
    return Response({
        'date': today,
        'checkin': AttendanceSerializer(checkin).data if checkin else None,
        'checkout': AttendanceSerializer(checkout).data if checkout else None,
        'has_checked_in': bool(checkin),
        'has_checked_out': bool(checkout),
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def attendance_summary(request):
    """Get attendance summary for current user"""
    user = request.user
    
    # Get date range from query params
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = date.today().replace(day=1)  # First day of current month
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = date.today()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get attendance records
    records = Attendance.objects.filter(
        user=user,
        date__range=[start_date, end_date],
        attendance_type='check_in'
    )
    
    # Calculate statistics
    total_days = (end_date - start_date).days + 1
    present_days = records.filter(status='present').count()
    late_days = records.filter(status='late').count()
    absent_days = total_days - records.count()
    
    # Calculate total hours worked
    total_hours = sum([record.hours_worked for record in records if record.hours_worked])
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days
        },
        'summary': {
            'present_days': present_days,
            'late_days': late_days,
            'absent_days': absent_days,
            'total_hours': round(total_hours, 2)
        },
        'attendance_rate': round((present_days + late_days) / total_days * 100, 2) if total_days > 0 else 0
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def face_recognition_checkin(request):
    """Face recognition based check-in"""
    user = request.user
    today = date.today()
    
    # Check if user already checked in today
    existing_checkin = Attendance.objects.filter(
        user=user,
        date=today,
        attendance_type='check_in'
    ).first()
    
    if existing_checkin:
        return Response(
            {'error': 'You have already checked in today.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get face image from request
    face_image = request.FILES.get('face_image')
    if not face_image:
        return Response(
            {'error': 'Face image is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get attendance settings
    settings = AttendanceSettings.get_settings()
    
    # Perform face recognition verification
    try:
        face_verified, message, face_confidence = FaceRecognitionUtils.verify_user_face(user, face_image)
        
        if not face_verified:
            logger.warning(f"Face verification failed for user {user.employee_id}: {message}")
            return Response(
                {'error': f'Face verification failed: {message}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if confidence meets threshold
        if face_confidence < settings.face_confidence_threshold:
            logger.warning(f"Face confidence {face_confidence:.2f} below threshold {settings.face_confidence_threshold} for user {user.employee_id}")
            return Response(
                {'error': f'Face recognition confidence too low. Please try again in better lighting.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Face recognition error for user {user.employee_id}: {str(e)}")
        return Response(
            {'error': 'Face recognition system error. Please try manual check-in or contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Get client IP address
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    
    # Create check-in record
    attendance = Attendance.objects.create(
        user=user,
        date=today,
        attendance_type='check_in',
        check_in_time=timezone.now(),
        face_verified=face_verified,
        face_confidence=face_confidence,
        face_image=face_image,
        latitude=request.data.get('latitude'),
        longitude=request.data.get('longitude'),
        location_accuracy=request.data.get('location_accuracy'),
        notes=request.data.get('notes', ''),
        ip_address=ip_address,
        device_info=request.META.get('HTTP_USER_AGENT', '')
    )
    
    logger.info(f"Face recognition check-in successful for user {user.employee_id} with confidence {face_confidence:.2f}")
    
    return Response({
        'message': 'Face recognition check-in successful',
        'attendance': AttendanceSerializer(attendance).data,
        'face_confidence': face_confidence,
        'verification_message': message
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def attendance_analytics(request):
    """Get attendance analytics (HR/Manager only)"""
    user = request.user
    if user.role not in ['hr', 'manager']:
        return Response(
            {'error': 'Only HR and Managers can view analytics.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = date.today().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = date.today()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get all attendance records in date range
    records = Attendance.objects.filter(
        date__range=[start_date, end_date],
        attendance_type='check_in'
    )
    
    # Calculate analytics
    total_records = records.count()
    present_count = records.filter(status='present').count()
    late_count = records.filter(status='late').count()
    
    # Department-wise analytics
    department_stats = {}
    for record in records:
        dept = record.user.department or 'Unknown'
        if dept not in department_stats:
            department_stats[dept] = {'present': 0, 'late': 0, 'total': 0}
        
        department_stats[dept]['total'] += 1
        if record.status == 'present':
            department_stats[dept]['present'] += 1
        elif record.status == 'late':
            department_stats[dept]['late'] += 1
    
    return Response({
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'overall_stats': {
            'total_records': total_records,
            'present_count': present_count,
            'late_count': late_count,
            'attendance_rate': round(present_count / total_records * 100, 2) if total_records > 0 else 0,
            'punctuality_rate': round((present_count / (present_count + late_count)) * 100, 2) if (present_count + late_count) > 0 else 0
        },
        'department_stats': department_stats
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def setup_face_recognition(request):
    """Setup face recognition for a user"""
    user = request.user
    
    # Get face image from request
    face_image = request.FILES.get('face_image')
    if not face_image:
        return Response(
            {'error': 'Face image is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Setup face recognition
    try:
        success, message, confidence = FaceRecognitionUtils.setup_user_face_recognition(user, face_image)
        
        if success:
            logger.info(f"Face recognition setup successful for user {user.employee_id}")
            return Response({
                'message': message,
                'success': True,
                'confidence': confidence
            }, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Face recognition setup failed for user {user.employee_id}: {message}")
            return Response(
                {'error': message, 'success': False},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Face recognition setup error for user {user.employee_id}: {str(e)}")
        return Response(
            {'error': 'Face recognition setup failed. Please try again.', 'success': False},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def face_recognition_checkout(request):
    """Face recognition based check-out"""
    user = request.user
    today = date.today()
    
    # Find today's check-in record
    checkin_record = Attendance.objects.filter(
        user=user,
        date=today,
        attendance_type='check_in'
    ).first()
    
    if not checkin_record:
        return Response(
            {'error': 'You must check in first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if already checked out
    existing_checkout = Attendance.objects.filter(
        user=user,
        date=today,
        attendance_type='check_out'
    ).first()
    
    if existing_checkout:
        return Response(
            {'error': 'You have already checked out today.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get face image from request
    face_image = request.FILES.get('face_image')
    if not face_image:
        return Response(
            {'error': 'Face image is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get attendance settings
    settings = AttendanceSettings.get_settings()
    
    # Perform face recognition verification
    try:
        face_utils = FaceRecognitionUtils()
        
        # Convert image to numpy array
        image_array = face_utils.preprocess_image(face_image)
        
        # Verify face against user's stored encoding
        match, confidence = face_utils.compare_faces(
            user.face_encoding,
            image_array
        )
        
        face_verified = match and confidence >= (settings.face_confidence_threshold * 100)
        face_confidence = confidence / 100  # Convert to 0-1 scale
        
        if not face_verified:
            logger.warning(f"Face verification failed for checkout - user {user.employee_id} (Confidence: {confidence:.2f}%)")
            return Response(
                {'error': 'Face verification failed. Your face was not recognized. Please try again.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        logger.info(f"Face verification successful for checkout - user {user.employee_id} (Confidence: {confidence:.2f}%)")
        
        # Save the face image for audit
        filename = f"checkout_{user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        face_image.name = filename
            
    except Exception as e:
        logger.error(f"Face recognition error for checkout - user {user.employee_id}: {str(e)}")
        return Response(
            {'error': 'Face recognition system error. Please try manual check-out or contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Get client IP address
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    checkout_time = timezone.now()
    
    # Create check-out record
    attendance = Attendance.objects.create(
        user=user,
        date=today,
        attendance_type='check_out',
        check_out_time=checkout_time,
        face_verified=face_verified,
        face_confidence=face_confidence,
        face_image=face_image,
        latitude=request.data.get('latitude'),
        longitude=request.data.get('longitude'),
        location_accuracy=request.data.get('location_accuracy'),
        notes=request.data.get('notes', ''),
        ip_address=ip_address,
        device_info=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Update check-in record with check-out time
    checkin_record.check_out_time = checkout_time
    checkin_record.save()
    
    logger.info(f"Face recognition check-out successful for user {user.employee_id} with confidence {face_confidence:.2f}")
    
    return Response({
        'message': 'Checked out successfully with face verification',
        'attendance': AttendanceSerializer(attendance).data,
        'face_verified': True,
        'face_confidence': face_confidence
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def face_recognition_status(request):
    """Check if user has face recognition set up"""
    user = request.user
    
    has_face_encoding = bool(user.face_encoding)
    
    return Response({
        'has_face_recognition': has_face_encoding,
        'employee_id': user.employee_id,
        'message': 'Face recognition is set up' if has_face_encoding else 'Face recognition not set up'
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_face_recognition(request):
    """Remove face recognition data for a user"""
    user = request.user
    
    if not user.face_encoding:
        return Response(
            {'error': 'Face recognition is not set up for this user.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Clear face encoding
    user.face_encoding = ''
    user.save()
    
    logger.info(f"Face recognition data removed for user {user.employee_id}")
    
    return Response({
        'message': 'Face recognition data removed successfully',
        'success': True
    })
