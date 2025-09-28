from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import models
from attendance.models import AttendanceSettings
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to set up face recognition system
    """
    help = 'Initialize face recognition system with default settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confidence-threshold',
            type=float,
            default=0.6,
            help='Set face recognition confidence threshold (0.0-1.0)'
        )
        parser.add_argument(
            '--enable-location',
            action='store_true',
            help='Enable location tracking for attendance'
        )
        parser.add_argument(
            '--office-lat',
            type=float,
            help='Office latitude for location tracking'
        )
        parser.add_argument(
            '--office-lng',
            type=float,
            help='Office longitude for location tracking'
        )
        parser.add_argument(
            '--location-radius',
            type=int,
            default=100,
            help='Allowed radius from office location in meters'
        )
        parser.add_argument(
            '--late-threshold',
            type=int,
            default=15,
            help='Minutes after shift start to mark as late'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing settings to defaults'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Setting up Face Recognition System...')
        )

        # Validate confidence threshold
        confidence = options['confidence_threshold']
        if not 0.0 <= confidence <= 1.0:
            raise CommandError('Confidence threshold must be between 0.0 and 1.0')

        # Check if settings already exist
        settings_exist = AttendanceSettings.objects.exists()
        if settings_exist and not options['reset']:
            self.stdout.write(
                self.style.WARNING(
                    'Attendance settings already exist. Use --reset to override.'
                )
            )
            settings = AttendanceSettings.objects.first()
            self.display_current_settings(settings)
            return

        # Create or update settings
        if options['reset'] and settings_exist:
            AttendanceSettings.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Existing settings have been reset.')
            )

        # Validate location settings
        enable_location = options['enable_location']
        office_lat = options['office_lat']
        office_lng = options['office_lng']

        if enable_location and (office_lat is None or office_lng is None):
            raise CommandError(
                'Office latitude and longitude are required when enabling location tracking'
            )

        # Create new settings
        settings = AttendanceSettings.objects.create(
            face_recognition_enabled=True,
            face_confidence_threshold=confidence,
            location_tracking_enabled=enable_location,
            location_radius_meters=options['location_radius'],
            office_latitude=office_lat,
            office_longitude=office_lng,
            late_threshold_minutes=options['late_threshold'],
            early_departure_threshold_minutes=30,
            require_photo_for_attendance=False,
            allow_manual_attendance=True
        )

        self.stdout.write(
            self.style.SUCCESS('✓ Face recognition system configured successfully!')
        )

        self.display_current_settings(settings)

        # Check for users without face recognition
        users_without_face = User.objects.filter(
            is_active=True
        ).filter(
            models.Q(face_encoding__isnull=True) | models.Q(face_encoding='')
        )

        if users_without_face.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'\nFound {users_without_face.count()} active users without face recognition setup:'
                )
            )
            for user in users_without_face[:10]:  # Show first 10
                self.stdout.write(f'  - {user.get_full_name()} ({user.employee_id})')
            
            if users_without_face.count() > 10:
                self.stdout.write(f'  ... and {users_without_face.count() - 10} more')

            self.stdout.write(
                self.style.WARNING(
                    '\nUsers need to set up face recognition through the mobile app.'
                )
            )

        # Installation check
        self.check_dependencies()

    def display_current_settings(self, settings):
        """Display current attendance settings"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('CURRENT ATTENDANCE SETTINGS'))
        self.stdout.write('='*50)
        
        self.stdout.write(f'Face Recognition: {"✓ Enabled" if settings.face_recognition_enabled else "✗ Disabled"}')
        self.stdout.write(f'Confidence Threshold: {settings.face_confidence_threshold:.1%}')
        self.stdout.write(f'Location Tracking: {"✓ Enabled" if settings.location_tracking_enabled else "✗ Disabled"}')
        
        if settings.location_tracking_enabled:
            self.stdout.write(f'Office Location: {settings.office_latitude}, {settings.office_longitude}')
            self.stdout.write(f'Allowed Radius: {settings.location_radius_meters}m')
        
        self.stdout.write(f'Late Threshold: {settings.late_threshold_minutes} minutes')
        self.stdout.write(f'Manual Attendance: {"✓ Allowed" if settings.allow_manual_attendance else "✗ Disabled"}')
        self.stdout.write(f'Photo Required: {"✓ Yes" if settings.require_photo_for_attendance else "✗ No"}')
        self.stdout.write('='*50 + '\n')

    def check_dependencies(self):
        """Check if required dependencies are installed"""
        self.stdout.write(self.style.SUCCESS('\nChecking dependencies...'))
        
        try:
            import face_recognition
            self.stdout.write('✓ face-recognition library installed')
        except ImportError:
            self.stdout.write(
                self.style.ERROR('✗ face-recognition library not found. Install with: pip install face-recognition')
            )

        try:
            import cv2
            self.stdout.write('✓ OpenCV library installed')
        except ImportError:
            self.stdout.write(
                self.style.ERROR('✗ OpenCV library not found. Install with: pip install opencv-python-headless')
            )

        try:
            import dlib
            self.stdout.write('✓ dlib library installed')
        except ImportError:
            self.stdout.write(
                self.style.ERROR('✗ dlib library not found. Install with: pip install dlib')
            )

        try:
            from utils.face_recognition_utils import FaceRecognitionUtils
            self.stdout.write('✓ Face recognition utilities available')
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Face recognition utilities not found: {e}')
            )

        self.stdout.write(
            self.style.SUCCESS('\nFace recognition system is ready to use!')
        )
        self.stdout.write(
            'Next steps:\n'
            '1. Run migrations: python manage.py migrate\n'
            '2. Install mobile app dependencies: npm install (in mobile_app directory)\n'
            '3. Users can set up face recognition through the mobile app\n'
        )
