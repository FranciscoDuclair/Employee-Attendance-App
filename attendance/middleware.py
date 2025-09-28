"""
Custom middleware for the Employee Attendance System
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger('attendance')


class SessionSecurityMiddleware:
    """
    Middleware to handle session security and timeout
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request before view
        self.process_request(request)
        
        response = self.get_response(request)
        
        # Process response after view
        return self.process_response(request, response)
    
    def process_request(self, request):
        """Process incoming request for security checks"""
        if request.user.is_authenticated:
            # Check session timeout
            if self._check_session_timeout(request):
                return self._handle_session_timeout(request)
            
            # Update last activity
            self._update_last_activity(request)
            
            # Check for password change requirement
            if self._check_password_change_required(request):
                return self._redirect_to_password_change(request)
    
    def process_response(self, request, response):
        """Process response for additional security headers"""
        if request.user.is_authenticated:
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            
            # Update session activity
            if hasattr(request, 'session'):
                request.session['last_activity'] = timezone.now().isoformat()
        
        return response
    
    def _check_session_timeout(self, request):
        """Check if session has timed out"""
        if not hasattr(request, 'session'):
            return False
        
        last_activity = request.session.get('last_activity')
        if not last_activity:
            return False
        
        try:
            last_activity_time = timezone.datetime.fromisoformat(last_activity)
            if timezone.is_naive(last_activity_time):
                last_activity_time = timezone.make_aware(last_activity_time)
            
            timeout_duration = getattr(settings, 'SESSION_TIMEOUT_MINUTES', 60)
            timeout_threshold = timezone.now() - timezone.timedelta(minutes=timeout_duration)
            
            return last_activity_time < timeout_threshold
        except (ValueError, TypeError):
            return False
    
    def _handle_session_timeout(self, request):
        """Handle session timeout"""
        from django.contrib.auth import logout
        
        logger.info(f'Session timeout for user: {request.user.email}')
        logout(request)
        messages.warning(request, 'Your session has expired. Please log in again.')
        return redirect('attendance_web:login')
    
    def _update_last_activity(self, request):
        """Update last activity timestamp"""
        if hasattr(request, 'session'):
            request.session['last_activity'] = timezone.now().isoformat()
    
    def _check_password_change_required(self, request):
        """Check if user needs to change password"""
        password_change_required = cache.get(f'password_change_required_{request.user.id}')
        return password_change_required and request.path != '/change-password/'
    
    def _redirect_to_password_change(self, request):
        """Redirect to password change page"""
        messages.warning(request, 'You must change your password before continuing.')
        return redirect('attendance_web:change_password')


class LoginAttemptMiddleware:
    """
    Middleware to track and limit login attempts
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log successful logins
        if (request.path == '/login/' and 
            request.method == 'POST' and 
            request.user.is_authenticated):
            self._log_successful_login(request)
        
        return response
    
    def _log_successful_login(self, request):
        """Log successful login attempt"""
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        logger.info(f'Successful login: {request.user.email} from {client_ip} - {user_agent}')
        
        # Store login history (optional)
        login_history_key = f'login_history_{request.user.id}'
        history = cache.get(login_history_key, [])
        
        login_record = {
            'timestamp': timezone.now().isoformat(),
            'ip': client_ip,
            'user_agent': user_agent
        }
        
        history.insert(0, login_record)
        history = history[:10]  # Keep last 10 logins
        
        cache.set(login_history_key, history, 86400 * 30)  # 30 days
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CSP header for additional security
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Content-Security-Policy'] = csp_policy
        
        return response
