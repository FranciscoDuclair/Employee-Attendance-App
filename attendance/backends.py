"""
Custom authentication backends for the Employee Attendance System
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import logging

User = get_user_model()
logger = logging.getLogger('attendance')


class EmailAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address
    instead of username, with additional security features.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # Normalize email
        email = username.lower().strip()
        
        try:
            # Get user by email
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        
        # Check if user account is active
        if not user.is_active:
            logger.warning(f'Login attempt for inactive user: {email}')
            return None
        
        # Check password
        if user.check_password(password):
            # Additional security checks
            if self._additional_security_checks(user, request):
                logger.info(f'Successful authentication: {email}')
                return user
            else:
                logger.warning(f'Failed additional security checks: {email}')
                return None
        
        logger.warning(f'Invalid password for user: {email}')
        return None
    
    def _additional_security_checks(self, user, request):
        """
        Perform additional security checks before allowing login
        """
        # Check if user has been locked by admin
        if hasattr(user, 'is_locked') and user.is_locked:
            return False
        
        # Check for suspicious activity patterns
        if self._check_suspicious_activity(user, request):
            return False
        
        # Check if account needs password change
        if self._password_needs_change(user):
            # Set flag for password change requirement
            cache.set(f'password_change_required_{user.id}', True, 3600)
        
        return True
    
    def _check_suspicious_activity(self, user, request):
        """
        Check for suspicious login patterns
        """
        if not request:
            return False
        
        client_ip = self._get_client_ip(request)
        
        # Check if login from new IP (simplified check)
        last_ip_key = f'last_login_ip_{user.id}'
        last_ip = cache.get(last_ip_key)
        
        if last_ip and last_ip != client_ip:
            # Log potential security concern
            logger.warning(f'Login from new IP for user {user.email}: {client_ip} (previous: {last_ip})')
        
        # Store current IP
        cache.set(last_ip_key, client_ip, 86400 * 30)  # 30 days
        
        return False  # Don't block for now, just log
    
    def _password_needs_change(self, user):
        """
        Check if user password needs to be changed
        """
        if not user.last_login:
            return True  # First time login
        
        # Check if password is older than 90 days
        password_age_limit = getattr(settings, 'PASSWORD_AGE_LIMIT_DAYS', 90)
        if user.last_login:
            days_since_login = (timezone.now() - user.last_login).days
            return days_since_login > password_age_limit
        
        return False
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_user(self, user_id):
        """
        Get user by ID with additional checks
        """
        try:
            user = User.objects.get(pk=user_id)
            if user.is_active:
                return user
        except User.DoesNotExist:
            pass
        return None


class FaceRecognitionAuthBackend(ModelBackend):
    """
    Authentication backend for face recognition login
    """
    
    def authenticate(self, request, user_id=None, face_confidence=None, **kwargs):
        if user_id is None or face_confidence is None:
            return None
        
        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None
        
        # Check if face recognition confidence meets threshold
        threshold = getattr(settings, 'FACE_RECOGNITION_SETTINGS', {}).get('CONFIDENCE_THRESHOLD', 0.6)
        
        if face_confidence >= threshold:
            logger.info(f'Successful face recognition login: {user.email} (confidence: {face_confidence})')
            return user
        
        logger.warning(f'Face recognition confidence too low: {user.email} (confidence: {face_confidence})')
        return None
