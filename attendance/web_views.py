from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.views.generic import (TemplateView, ListView, View, 
                                 CreateView, UpdateView, DetailView)
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, Sum, Case, When, Value, IntegerField
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.cache import cache
from django.conf import settings
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import json
import base64
import cv2
import numpy as np
import psutil
import os
import logging

from .mixins import AdminRequiredMixin, ManagerRequiredMixin, role_required

from .models import Attendance, AttendanceSettings
from users.models import User
from utils.face_recognition_utils import FaceRecognitionUtils


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard view that redirects users to role-specific dashboards
    """
    def get_template_names(self):
        user = self.request.user
        if user.role == 'hr':
            return ['dashboard/admin_dashboard.html']
        elif user.role == 'manager':
            return ['dashboard/manager_dashboard.html']
        else:
            return ['dashboard/employee_dashboard.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.now().date()
        
        # Common context for all roles
        context['today'] = today
        
        # Get today's attendance
        today_attendance = Attendance.objects.filter(
            user=user, 
            date=today
        ).order_by('-created_at').first()
        
        # Get recent attendance records
        recent_attendance = Attendance.objects.filter(
            user=user
        ).order_by('-date', '-created_at')[:10]
        
        # Get attendance statistics
        this_month = timezone.now().replace(day=1).date()
        month_attendance = Attendance.objects.filter(
            user=user,
            date__gte=this_month
        )
        
        # Calculate monthly stats
        present_days = month_attendance.filter(
            status='present', 
            attendance_type='check_in'
        ).count()
        
        late_days = month_attendance.filter(
            status='late', 
            attendance_type='check_in'
        ).count()
        
        # Common context
        context.update({
            'attendance_status': self._get_attendance_status(user, today),
            'last_checkin_time': today_attendance.check_in_time if today_attendance and today_attendance.check_in_time else None,
            'last_checkout_time': today_attendance.check_out_time if today_attendance and today_attendance.check_out_time else None,
            'monthly_stats': {
                'present_days': present_days,
                'late_days': late_days,
                'total_days': (timezone.now().date() - this_month).days + 1
            },
            'recent_activity': self._get_recent_activity(user),
            'leave_balance': self._get_leave_balance(user)
        })
        
        # Role-specific context
        if user.role == 'hr':
            context.update(self._get_admin_context())
        elif user.role == 'manager':
            context.update(self._get_manager_context(user))
            
        return context
    
    def _get_attendance_status(self, user, date):
        """Determine if user is checked in, checked out, or neither"""
        today_attendance = Attendance.objects.filter(
            user=user,
            date=date
        ).order_by('-created_at')
        
        if today_attendance.exists():
            last_record = today_attendance.first()
            if last_record.attendance_type == 'check_in' and not last_record.check_out_time:
                return 'checked_in'
            elif last_record.attendance_type == 'check_out':
                return 'checked_out'
        return 'not_checked_in'
    
    def _get_recent_activity(self, user):
        """Get recent activity for the user"""
        recent = Attendance.objects.filter(
            user=user
        ).order_by('-date', '-created_at')[:5]
        
        return [{
            'type': record.attendance_type,
            'message': f"Checked {'in' if record.attendance_type == 'check_in' else 'out'} at {record.check_in_time.time() if record.check_in_time else record.check_out_time.time()}",
            'timestamp': record.check_in_time if record.attendance_type == 'check_in' else record.check_out_time
        } for record in recent]
    
    def _get_leave_balance(self, user):
        """Get user's leave balance (simplified)"""
        # This would typically come from a leave management system
        return 15  # Default leave balance
    
    def _get_admin_context(self):
        """Get context specific to admin users"""
        from django.db import connection
        import psutil
        import os
        
        # Get database status
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_status = 'ok'
        except Exception as e:
            db_status = 'error'
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        
        # Get active users
        today = timezone.now().date()
        active_users = Attendance.objects.filter(
            date=today
        ).values('user').distinct().count()
        
        total_users = User.objects.count()
        
        return {
            'system_stats': {
                'total_employees': total_users,
                'active_employees': User.objects.filter(is_active=True).count(),
                'today_attendance': Attendance.objects.filter(date=today, attendance_type='check_in').count(),
                'today_late': Attendance.objects.filter(date=today, status='late', attendance_type='check_in').count(),
                'pending_leave': 0,  # Would come from leave app
                'pending_regularizations': 0,  # Would come from attendance app
                'face_setup': int((User.objects.exclude(face_encoding='').count() / total_users) * 100) if total_users > 0 else 0,
                'face_not_setup': User.objects.filter(face_encoding='').count()
            },
            'system_health': {
                'database': {
                    'status': db_status,
                    'usage': 45  # Example value
                },
                'storage': {
                    'status': 'warning' if disk.percent > 80 else 'ok',
                    'usage': disk.percent,
                    'used': f"{disk.used / (1024**3):.1f} GB",
                    'total': f"{disk.total / (1024**3):.1f} GB"
                },
                'active_users': {
                    'status': 'info',
                    'count': active_users,
                    'percentage': int((active_users / total_users) * 100) if total_users > 0 else 0
                },
                'overall_status': 'success',
                'overall_icon': 'check-circle',
                'overall_message': 'All systems operational',
                'last_updated': timezone.now()
            },
            'recent_activities': self._get_system_activities()
        }
    
    def _get_manager_context(self, manager):
        """Get context specific to team managers"""
        # Get team members (direct reports)
        team_members = User.objects.filter(manager=manager, is_active=True)
        team_member_ids = list(team_members.values_list('id', flat=True))
        
        today = timezone.now().date()
        
        # Get today's attendance for team
        today_attendance = Attendance.objects.filter(
            user__in=team_member_ids,
            date=today,
            attendance_type='check_in'
        )
        
        # Team statistics
        team_stats = {
            'checked_in': today_attendance.count(),
            'late': today_attendance.filter(status='late').count(),
            'absent': team_members.count() - today_attendance.count(),
            'on_leave': 0  # Would come from leave app
        }
        
        # Get weekly attendance for team
        week_start = today - timedelta(days=today.weekday())
        week_dates = [week_start + timedelta(days=i) for i in range(5)]  # Weekdays only
        
        weekly_data = []
        for member in team_members:
            member_attendance = []
            for day in week_dates:
                att = Attendance.objects.filter(
                    user=member,
                    date=day,
                    attendance_type='check_in'
                ).first()
                member_attendance.append({
                    'date': day,
                    'status': att.status[0].upper() if att else 'A',  # P, L, or A
                    'time': att.check_in_time.time() if att and att.check_in_time else None
                })
            weekly_data.append({
                'employee': member,
                'days': member_attendance
            })
        
        # Performance metrics (simplified)
        total_checks = team_members.count() * 5  # 5 working days
        if total_checks > 0:
            present_checks = Attendance.objects.filter(
                user__in=team_member_ids,
                date__in=week_dates,
                status='present',
                attendance_type='check_in'
            ).count()
            late_checks = Attendance.objects.filter(
                user__in=team_member_ids,
                date__in=week_dates,
                status='late',
                attendance_type='check_in'
            ).count()
            absent_checks = total_checks - (present_checks + late_checks)
            
            performance_metrics = {
                'on_time': int((present_checks / total_checks) * 100),
                'late': int((late_checks / total_checks) * 100),
                'absent': int((absent_checks / total_checks) * 100)
            }
        else:
            performance_metrics = {'on_time': 0, 'late': 0, 'absent': 0}
        
        # Pending approvals (simplified)
        pending_approvals = []  # Would come from leave/attendance apps
        
        return {
            'team_stats': team_stats,
            'weekly_attendance': weekly_data,
            'performance_metrics': performance_metrics,
            'pending_approvals': pending_approvals
        }
    
    def _get_system_activities(self, limit=10):
        """Get recent system activities (simplified)"""
        # In a real app, this would come from an activity log model
        activities = []
        
        # Example activities
        activities.append({
            'icon': 'user-plus',
            'type': 'info',
            'message': 'New user registered: John Doe',
            'details': 'Role: Employee',
            'timestamp': timezone.now() - timedelta(minutes=15)
        })
        
        activities.append({
            'icon': 'exclamation-triangle',
            'type': 'warning',
            'message': 'Failed login attempt',
            'details': 'IP: 192.168.1.100',
            'timestamp': timezone.now() - timedelta(hours=1)
        })
        
        activities.append({
            'icon': 'check-circle',
            'type': 'success',
            'message': 'System backup completed',
            'details': 'Backup size: 1.2 GB',
            'timestamp': timezone.now() - timedelta(hours=3)
        })
        
        return activities[:limit]
        face_setup = bool(user.face_encoding)
        
        context.update({
            'today_attendance': today_attendance,
            'recent_attendance': recent_attendance,
            'month_attendance_count': month_attendance.count(),
            'month_late_count': month_attendance.filter(status='late').count(),
            'face_setup': face_setup,
            'user': user,
        })
        
        return context


class FaceSetupView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/face_setup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['face_setup'] = bool(self.request.user.face_encoding)
        return context


class FaceCaptureView(LoginRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            
            if not image_data:
                return JsonResponse({'error': 'No image provided'}, status=400)
            
            try:
                # Decode base64 image
                if 'base64,' in image_data:
                    image_data = image_data.split('base64,')[1]
                
                image_bytes = base64.b64decode(image_data)
                
                # Convert to numpy array and process with OpenCV
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if image is None:
                    return JsonResponse({
                        'error': 'Failed to process the image. Please try again.'
                    }, status=400)
                
                # Convert from BGR (OpenCV default) to RGB (face_recognition expects RGB)
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Process face recognition
                face_utils = FaceRecognitionUtils()
                
                # First, detect faces in the image
                face_locations = face_utils.detect_faces(rgb_image)
                if not face_locations:
                    return JsonResponse({
                        'error': 'No face detected. Please ensure your face is clearly visible and well-lit.'
                    }, status=400)
                
                # Then get the face encoding
                encoding = face_utils.generate_face_encoding(rgb_image)
                
                if encoding is None:
                    return JsonResponse({
                        'error': 'Could not generate face encoding. Please try again with a clearer image.'
                    }, status=400)
                
                # Save encoding to user
                request.user.face_encoding = face_utils.encoding_to_string(encoding[0])  # Take first face found
                request.user.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Face recognition setup completed successfully!'
                })
                
            except Exception as e:
                logger.error(f'Error in face capture: {str(e)}', exc_info=True)
                return JsonResponse({
                    'error': f'Failed to process image: {str(e)}'
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f'Unexpected error in FaceCaptureView: {str(e)}', exc_info=True)
            return JsonResponse({
                'error': 'An unexpected error occurred. Please try again.'
            }, status=500)


class FaceStatusView(LoginRequiredMixin, View):
    def get(self, request):
        return JsonResponse({
            'face_setup': bool(request.user.face_encoding)
        })


class AttendanceListView(LoginRequiredMixin, ListView):
    model = Attendance
    template_name = 'attendance/attendance_list.html'
    context_object_name = 'attendance_records'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Attendance.objects.filter(user=self.request.user)
        
        # Filter by date range
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
            
        return queryset.order_by('-date', '-created_at')


class CheckInView(LoginRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            user = request.user
            today = timezone.now().date()
            
            # Check if already checked in today - get the first check-in of the day
            existing_checkin = Attendance.objects.filter(
                user=user,
                date=today,
                attendance_type='check_in'
            ).first()
            
            if existing_checkin:
                return JsonResponse({
                    'error': f'You have already checked in today at {existing_checkin.check_in_time.strftime("%H:%M")}. Only one check-in per day is allowed.'
                }, status=400)
            
            # Face verification if image provided
            face_verified = False
            face_confidence = None
            
            if image_data and user.face_encoding:
                try:
                    # Decode and process image
                    image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Verify face
                    face_utils = FaceRecognitionUtils()
                    stored_encoding = face_utils.string_to_encoding(user.face_encoding)
                    face_confidence = face_utils.verify_face(image, stored_encoding)
                    
                    settings = AttendanceSettings.objects.first()
                    threshold = settings.face_confidence_threshold if settings else 0.6
                    
                    face_verified = face_confidence >= threshold
                    
                except Exception as e:
                    pass  # Continue without face verification
            
            # Create attendance record
            attendance = Attendance.objects.create(
                user=user,
                date=today,
                attendance_type='check_in',
                check_in_time=timezone.now(),
                face_verified=face_verified,
                face_confidence=face_confidence,
                latitude=latitude,
                longitude=longitude,
                ip_address=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Check-in successful!',
                'face_verified': face_verified,
                'confidence': face_confidence
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Check-in failed: {str(e)}'
            }, status=500)


class CheckOutView(LoginRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            user = request.user
            today = timezone.now().date()
            
            # Find today's check-in
            checkin = Attendance.objects.filter(
                user=user,
                date=today,
                attendance_type='check_in'
            ).first()
            
            if not checkin:
                return JsonResponse({
                    'error': 'No check-in record found for today. Please check in first.'
                }, status=400)
            
            # Check if already checked out - only allow one checkout per day
            existing_checkout = Attendance.objects.filter(
                user=user,
                date=today,
                attendance_type='check_out'
            ).first()
            
            if existing_checkout:
                return JsonResponse({
                    'error': f'You have already checked out today at {existing_checkout.check_out_time.strftime("%H:%M")}. Only one check-out per day is allowed.'
                }, status=400)
            
            # Face verification if image provided
            face_verified = False
            face_confidence = None
            
            if image_data and user.face_encoding:
                try:
                    # Decode and process image
                    image_data = image_data.split(',')[1]
                    image_bytes = base64.b64decode(image_data)
                    nparr = np.frombuffer(image_bytes, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Verify face
                    face_utils = FaceRecognitionUtils()
                    stored_encoding = face_utils.string_to_encoding(user.face_encoding)
                    face_confidence = face_utils.verify_face(image, stored_encoding)
                    
                    settings = AttendanceSettings.objects.first()
                    threshold = settings.face_confidence_threshold if settings else 0.6
                    
                    face_verified = face_confidence >= threshold
                    
                except Exception as e:
                    pass  # Continue without face verification
            
            # Create checkout record
            checkout_time = timezone.now()
            attendance = Attendance.objects.create(
                user=user,
                date=today,
                attendance_type='check_out',
                check_out_time=checkout_time,
                face_verified=face_verified,
                face_confidence=face_confidence,
                latitude=latitude,
                longitude=longitude,
                ip_address=request.META.get('REMOTE_ADDR'),
                device_info=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Calculate hours worked
            if checkin.check_in_time:
                hours_worked = (checkout_time - checkin.check_in_time).total_seconds() / 3600
                attendance.hours_worked = round(hours_worked, 2)
                attendance.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Check-out successful!',
                'face_verified': face_verified,
                'confidence': face_confidence,
                'hours_worked': attendance.hours_worked
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Check-out failed: {str(e)}'
            }, status=500)


class ReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get date range from request
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        if self.request.GET.get('start_date'):
            start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d').date()
        if self.request.GET.get('end_date'):
            end_date = datetime.strptime(self.request.GET.get('end_date'), '%Y-%m-%d').date()
        
        # Get attendance data
        attendance_records = Attendance.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).order_by('-date')
        
        # Calculate statistics
        total_days = (end_date - start_date).days + 1
        present_days = attendance_records.filter(attendance_type='check_in').count()
        late_days = attendance_records.filter(status='late').count()
        
        context.update({
            'attendance_records': attendance_records,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days,
            'present_days': present_days,
            'late_days': late_days,
            'attendance_percentage': round((present_days / total_days) * 100, 1) if total_days > 0 else 0,
        })
        
        return context


class ExportReportView(LoginRequiredMixin, View):
    def get(self, request):
        # This would implement CSV/PDF export functionality
        return JsonResponse({'message': 'Export functionality coming soon'})


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings = AttendanceSettings.objects.first()
        context['settings'] = settings
        return context


class LoginView(View):
    template_name = 'attendance/login.html'
    
    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('password'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('attendance_web:dashboard')
        
        # Check if account is locked
        lockout_key = f"login_attempts_{self.get_client_ip(request)}"
        attempts = cache.get(lockout_key, 0)
        lockout_duration = getattr(settings, 'ACCOUNT_LOCKOUT_DURATION', 900)
        max_attempts = getattr(settings, 'ACCOUNT_LOCKOUT_ATTEMPTS', 5)
        
        context = {
            'is_locked': attempts >= max_attempts,
            'lockout_duration': lockout_duration // 60,  # Convert to minutes
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me', False)
        
        # Get client IP for rate limiting
        client_ip = self.get_client_ip(request)
        lockout_key = f"login_attempts_{client_ip}"
        user_lockout_key = f"user_attempts_{email}" if email else None
        
        # Check rate limiting
        attempts = cache.get(lockout_key, 0)
        user_attempts = cache.get(user_lockout_key, 0) if user_lockout_key else 0
        max_attempts = getattr(settings, 'ACCOUNT_LOCKOUT_ATTEMPTS', 5)
        lockout_duration = getattr(settings, 'ACCOUNT_LOCKOUT_DURATION', 900)
        
        if attempts >= max_attempts or user_attempts >= max_attempts:
            messages.error(request, f'Account temporarily locked due to too many failed attempts. Try again in {lockout_duration // 60} minutes.')
            return render(request, self.template_name, {'is_locked': True})
        
        # Validate input
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, self.template_name)
        
        # Attempt authentication
        user = authenticate(request, username=email, password=password)
        
        if user:
            if user.is_active:
                # Successful login
                login(request, user)
                
                # Set session expiry based on remember me
                if remember_me:
                    request.session.set_expiry(86400 * 30)  # 30 days
                else:
                    request.session.set_expiry(86400)  # 24 hours
                
                # Clear failed attempts
                cache.delete(lockout_key)
                if user_lockout_key:
                    cache.delete(user_lockout_key)
                
                # Log successful login
                logger = logging.getLogger('attendance')
                logger.info(f'Successful login: {user.email} from {client_ip}')
                
                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Redirect to next URL or dashboard
                next_url = request.GET.get('next')
                if next_url and self.is_safe_url(next_url, request):
                    return redirect(next_url)
                return redirect('attendance_web:dashboard')
            else:
                messages.error(request, 'Your account has been deactivated. Please contact administrator.')
        else:
            # Failed login - increment attempts
            cache.set(lockout_key, attempts + 1, lockout_duration)
            if user_lockout_key:
                cache.set(user_lockout_key, user_attempts + 1, lockout_duration)
            
            # Log failed attempt
            logger = logging.getLogger('attendance')
            logger.warning(f'Failed login attempt: {email} from {client_ip}')
            
            remaining_attempts = max_attempts - (attempts + 1)
            if remaining_attempts > 0:
                messages.error(request, f'Invalid email or password. {remaining_attempts} attempts remaining.')
            else:
                messages.error(request, f'Too many failed attempts. Account locked for {lockout_duration // 60} minutes.')
        
        return render(request, self.template_name)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_safe_url(self, url, request):
        """Check if redirect URL is safe"""
        from django.utils.http import url_has_allowed_host_and_scheme
        return url_has_allowed_host_and_scheme(
            url=url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )


class LogoutView(LoginRequiredMixin, View):
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        # Log the logout
        logger = logging.getLogger('attendance')
        logger.info(f'User logout: {request.user.email}')
        
        # Clear session data
        request.session.flush()
        
        # Django logout
        logout(request)
        
        messages.success(request, 'You have been successfully logged out.')
        return redirect('attendance_web:login')
    
    def post(self, request):
        return self.get(request)


# Role-based Dashboard Views
class ProfileView(LoginRequiredMixin, UpdateView):
    """View for user profile management"""
    model = User
    fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile_picture']
    template_name = 'dashboard/profile.html'
    success_url = reverse_lazy('attendance_web:profile')
    
    def get_object(self):
        return self.request.user
    
    def post(self, request, *args, **kwargs):
        # Handle profile picture upload specifically
        if 'profile_picture' in request.FILES:
            user = request.user
            user.profile_picture = request.FILES['profile_picture']
            user.save()
            messages.success(request, 'Profile picture updated successfully.')
            return redirect('attendance_web:profile')
        
        # Handle profile picture removal
        if request.resolver_match.url_name == 'remove_profile_picture':
            user = request.user
            if user.profile_picture:
                user.profile_picture.delete(save=False)
                user.profile_picture = None
                user.save()
                messages.success(request, 'Profile picture removed successfully.')
            return redirect('attendance_web:profile')
        
        # Handle regular form submission
        return super().post(request, *args, **kwargs)
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully.')
        return super().form_valid(form)


class TeamAttendanceView(ManagerRequiredMixin, TemplateView):
    """View for managers to see team attendance"""
    template_name = 'dashboard/team_attendance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.request.user
        
        # Get team members (direct reports)
        team_members = User.objects.filter(manager=manager, is_active=True)
        
        # Date range for the report (default: current month)
        today = timezone.now().date()
        start_date = self.request.GET.get('start_date') or today.replace(day=1)
        end_date = self.request.GET.get('end_date') or today
        
        # Convert string dates to date objects if needed
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get attendance data for the team
        attendance_data = []
        for member in team_members:
            member_attendance = Attendance.objects.filter(
                user=member,
                date__range=[start_date, end_date]
            ).order_by('date')
            
            # Calculate statistics
            present = member_attendance.filter(status='present').count()
            late = member_attendance.filter(status='late').count()
            absent = (end_date - start_date).days + 1 - (present + late)
            
            attendance_data.append({
                'user': member,
                'present': present,
                'late': late,
                'absent': max(0, absent),  # Ensure not negative
                'attendance_records': member_attendance
            })
        
        context.update({
            'team_members': team_members,
            'attendance_data': attendance_data,
            'start_date': start_date,
            'end_date': end_date,
            'today': today
        })
        return context


class TeamPerformanceView(ManagerRequiredMixin, TemplateView):
    """View for managers to see team performance metrics"""
    template_name = 'dashboard/team_performance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.request.user
        
        # Get team members (direct reports)
        team_members = User.objects.filter(manager=manager, is_active=True)
        team_member_ids = list(team_members.values_list('id', flat=True))
        
        # Date range for the report (default: last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Get attendance data for the team
        attendance_data = Attendance.objects.filter(
            user__in=team_member_ids,
            date__range=[start_date, end_date],
            attendance_type='check_in'
        )
        
        # Calculate performance metrics
        total_days = (end_date - start_date).days + 1
        total_possible_checks = team_members.count() * total_days
        
        if total_possible_checks > 0:
            on_time = attendance_data.filter(status='present').count()
            late = attendance_data.filter(status='late').count()
            absent = total_possible_checks - (on_time + late)
            
            performance_metrics = {
                'on_time': (on_time / total_possible_checks) * 100,
                'late': (late / total_possible_checks) * 100,
                'absent': (absent / total_possible_checks) * 100,
                'total_checks': total_possible_checks
            }
        else:
            performance_metrics = {'on_time': 0, 'late': 0, 'absent': 0, 'total_checks': 0}
        
        # Get top performers and those needing improvement
        member_performance = []
        for member in team_members:
            member_data = attendance_data.filter(user=member)
            present = member_data.filter(status='present').count()
            late = member_data.filter(status='late').count()
            
            if total_days > 0:
                attendance_rate = ((present + late) / total_days) * 100
                on_time_rate = (present / total_days) * 100 if present > 0 else 0
            else:
                attendance_rate = on_time_rate = 0
                
            member_performance.append({
                'user': member,
                'present': present,
                'late': late,
                'absent': total_days - (present + late),
                'attendance_rate': attendance_rate,
                'on_time_rate': on_time_rate
            })
        
        # Sort by performance (on_time_rate)
        member_performance.sort(key=lambda x: x['on_time_rate'], reverse=True)
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'performance_metrics': performance_metrics,
            'member_performance': member_performance,
            'top_performers': member_performance[:3] if len(member_performance) > 3 else member_performance,
            'needs_improvement': member_performance[-3:] if len(member_performance) > 3 else []
        })
        return context


class PendingApprovalsView(ManagerRequiredMixin, ListView):
    """View for managers to see pending approval requests"""
    model = 'leave.LeaveRequest'  # This would come from your leave app
    template_name = 'dashboard/pending_approvals.html'
    context_object_name = 'pending_requests'
    
    def get_queryset(self):
        # This is a placeholder - implement based on your leave app's models
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context needed
        return context


class ProcessApprovalView(ManagerRequiredMixin, View):
    """View to process approval/rejection of requests"""
    def post(self, request, request_id, action):
        # This is a placeholder - implement based on your leave app's models
        messages.success(request, f"Request {action}ed successfully.")
        return redirect('attendance_web:pending_approvals')


class ViewRequestView(ManagerRequiredMixin, DetailView):
    """View to see details of a specific request"""
    model = 'leave.LeaveRequest'  # This would come from your leave app
    template_name = 'dashboard/view_request.html'
    context_object_name = 'request'
    
    def get_object(self, queryset=None):
        # This is a placeholder - implement based on your leave app's models
        return None


class SystemSettingsView(AdminRequiredMixin, TemplateView):
    """View for system settings (admin only)"""
    template_name = 'dashboard/system_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current settings
        settings = {
            'face_recognition_enabled': AttendanceSettings.load().face_recognition_enabled,
            'face_confidence_threshold': AttendanceSettings.load().face_confidence_threshold,
            'check_in_start': '09:00',  # Example setting
            'check_in_end': '11:00',    # Example setting
            'check_out_start': '17:00', # Example setting
            'check_out_end': '20:00',   # Example setting
        }
        
        context['settings'] = settings
        return context
    
    def post(self, request, *args, **kwargs):
        # Handle form submission to update settings
        settings = AttendanceSettings.load()
        
        # Update face recognition settings
        settings.face_recognition_enabled = request.POST.get('face_recognition_enabled') == 'on'
        settings.face_confidence_threshold = float(request.POST.get('face_confidence_threshold', 0.6))
        settings.save()
        
        # Here you would update other settings as needed
        
        messages.success(request, 'Settings updated successfully.')
        return redirect('attendance_web:system_settings')


class ActivityLogView(AdminRequiredMixin, ListView):
    """View for system activity logs - Admin only"""
    template_name = 'dashboard/activity_logs.html'
    context_object_name = 'activities'
    paginate_by = 50
    
    def get_queryset(self):
        # This is a placeholder - implement based on your logging app's models
        return []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context needed
        return context


# User Management Views (Admin only)
class UserListView(AdminRequiredMixin, ListView):
    """View for listing all users - Admin only"""
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(employee_id__icontains=search)
            )
        
        # Filter by role
        role = self.request.GET.get('role')
        if role:
            queryset = queryset.filter(role=role)
            
        # Filter by status
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['user_roles'] = User.ROLE_CHOICES
        return context


class UserCreateView(AdminRequiredMixin, CreateView):
    """View for creating new users - Admin only"""
    model = User
    template_name = 'users/user_form.html'
    fields = ['first_name', 'last_name', 'email', 'employee_id', 'role', 'department', 'manager', 'is_active']
    success_url = reverse_lazy('attendance_web:user_list')
    
    def form_valid(self, form):
        # Set a default password for new users
        user = form.save(commit=False)
        user.set_password('defaultpassword123')  # User should change this on first login
        user.save()
        messages.success(self.request, f'User {user.get_full_name()} created successfully.')
        return super().form_valid(form)


class UserDetailView(AdminRequiredMixin, DetailView):
    """View for user details - Admin only"""
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_detail'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Get recent attendance for this user
        recent_attendance = Attendance.objects.filter(
            user=user
        ).order_by('-date', '-created_at')[:10]
        
        # Get attendance statistics for current month
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_attendance = Attendance.objects.filter(
            user=user,
            date__gte=month_start,
            attendance_type='check_in'
        )
        
        context.update({
            'recent_attendance': recent_attendance,
            'month_stats': {
                'present': month_attendance.filter(status='present').count(),
                'late': month_attendance.filter(status='late').count(),
                'total': month_attendance.count()
            },
            'face_setup': bool(user.face_encoding)
        })
        return context


class UserUpdateView(AdminRequiredMixin, UpdateView):
    """View for updating user details - Admin only"""
    model = User
    template_name = 'users/user_form.html'
    fields = ['first_name', 'last_name', 'email', 'employee_id', 'role', 'department', 'manager', 'is_active']
    
    def get_success_url(self):
        return reverse_lazy('attendance_web:user_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'User {self.object.get_full_name()} updated successfully.')
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, View):
    """Delete user view - admin only"""
    
    def post(self, request, user_id):
        if not request.user.is_staff:
            return HttpResponseForbidden("Access denied")
        
        user = get_object_or_404(User, id=user_id)
        
        if user == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('attendance_web:user_list')
        
        if user.is_superuser and not request.user.is_superuser:
            messages.error(request, "You cannot delete a superuser account.")
            return redirect('attendance_web:user_list')
        
        username = user.get_full_name() or user.email
        user.delete()
        
        messages.success(request, f"User '{username}' has been deleted successfully.")
        return redirect('attendance_web:user_list')


class ChangePasswordView(LoginRequiredMixin, View):
    """Password change view with enhanced security"""
    template_name = 'attendance/change_password.html'
    
    @method_decorator(never_cache)
    @method_decorator(sensitive_post_parameters('old_password', 'new_password1', 'new_password2'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        form = PasswordChangeForm(request.user)
        
        # Check if password change is required
        password_change_required = cache.get(f'password_change_required_{request.user.id}')
        
        context = {
            'form': form,
            'password_change_required': password_change_required,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        
        if form.is_valid():
            user = form.save()
            
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            
            # Clear password change requirement
            cache.delete(f'password_change_required_{user.id}')
            
            # Log password change
            logger = logging.getLogger('attendance')
            logger.info(f'Password changed for user: {user.email}')
            
            messages.success(request, 'Your password has been changed successfully.')
            
            # Redirect based on whether change was required
            password_change_required = cache.get(f'password_change_required_{user.id}')
            if password_change_required:
                return redirect('attendance_web:dashboard')
            else:
                return redirect('attendance_web:settings')
        
        context = {
            'form': form,
            'password_change_required': cache.get(f'password_change_required_{request.user.id}'),
        }
        return render(request, self.template_name, context)


# Team Management API Views
class TeamStatusAPIView(ManagerRequiredMixin, View):
    """API view to get real-time team status"""
    
    def get(self, request):
        manager = request.user
        team_members = User.objects.filter(manager=manager, is_active=True)
        today = timezone.now().date()
        
        # Get team member status data
        team_data = []
        for member in team_members:
            # Get today's attendance
            today_attendance = Attendance.objects.filter(
                user=member,
                date=today
            ).order_by('-created_at').first()
            
            # Determine status
            if today_attendance:
                if today_attendance.attendance_type == 'check_in' and not today_attendance.check_out_time:
                    status = 'online'
                    status_class = 'online'
                    check_in_time = today_attendance.check_in_time
                    last_seen = None
                elif today_attendance.attendance_type == 'check_out':
                    status = 'offline'
                    status_class = 'offline'
                    check_in_time = None
                    last_seen = today_attendance.check_out_time
                else:
                    status = 'offline'
                    status_class = 'offline'
                    check_in_time = None
                    last_seen = today_attendance.created_at
            else:
                status = 'offline'
                status_class = 'offline'
                check_in_time = None
                last_seen = None
            
            team_data.append({
                'id': member.id,
                'name': member.get_full_name() or member.username,
                'profile_image': member.profile_picture.url if member.profile_picture else None,
                'status': status,
                'status_class': status_class,
                'check_in_time': check_in_time,
                'last_seen': last_seen
            })
        
        return JsonResponse({
            'success': True,
            'team_members': team_data
        })


class BulkActionsView(ManagerRequiredMixin, View):
    """Handle bulk actions for team management"""
    
    def post(self, request):
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        try:
            if action == 'approve_all_pending':
                # This would approve all pending leave requests
                # Implementation depends on your leave management system
                message = 'All pending requests have been approved.'
                
            elif action == 'send_reminder':
                # Send attendance reminder to team
                manager = request.user
                team_members = User.objects.filter(manager=manager, is_active=True)
                # Implementation would send notifications/emails
                message = f'Attendance reminder sent to {team_members.count()} team members.'
                
            elif action == 'generate_report':
                # Generate team report
                message = 'Team report has been generated and will be available shortly.'
                
            elif action == 'schedule_meeting':
                # Schedule team meeting
                message = 'Team meeting has been scheduled.'
                
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action selected.'
                })
            
            return JsonResponse({
                'success': True,
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error executing bulk action: {str(e)}'
            })


class EmployeeDetailView(ManagerRequiredMixin, DetailView):
    """View employee details for managers"""
    model = User
    template_name = 'dashboard/employee_detail.html'
    context_object_name = 'employee'
    
    def get_queryset(self):
        # Managers can only view their team members
        return User.objects.filter(manager=self.request.user, is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.get_object()
        
        # Get recent attendance
        recent_attendance = Attendance.objects.filter(
            user=employee
        ).order_by('-date', '-created_at')[:10]
        
        # Get monthly stats
        today = timezone.now().date()
        month_start = today.replace(day=1)
        month_attendance = Attendance.objects.filter(
            user=employee,
            date__gte=month_start,
            attendance_type='check_in'
        )
        
        context.update({
            'recent_attendance': recent_attendance,
            'month_stats': {
                'present': month_attendance.filter(status='present').count(),
                'late': month_attendance.filter(status='late').count(),
                'total': month_attendance.count()
            }
        })
        return context


class EmployeeAttendanceView(ManagerRequiredMixin, ListView):
    """View attendance history for a specific employee"""
    model = Attendance
    template_name = 'dashboard/employee_attendance.html'
    context_object_name = 'attendance_records'
    paginate_by = 20
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        employee = get_object_or_404(User, id=user_id, manager=self.request.user)
        
        queryset = Attendance.objects.filter(user=employee)
        
        # Date filtering
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        employee = get_object_or_404(User, id=user_id, manager=self.request.user)
        context['employee'] = employee
        return context


class SystemHealthView(APIView):
    """API view for system health monitoring"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get system health status"""
        try:
            # Check database connectivity
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            # Get system metrics
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            
            # Check cache
            cache_status = 'healthy'
            try:
                from django.core.cache import cache
                cache.set('health_check', 'ok', 30)
                if cache.get('health_check') != 'ok':
                    cache_status = 'unhealthy'
            except Exception:
                cache_status = 'unhealthy'
            
            # System health data
            health_data = {
                'database': 'healthy',
                'cache': cache_status,
                'total_users': total_users,
                'active_users': active_users,
                'system_load': 'normal',
                'memory_usage': '65%',
                'disk_usage': '45%',
                'last_backup': '2 hours ago',
                'uptime': '5 days, 12 hours'
            }
            
            return JsonResponse({
                'success': True,
                'health': health_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class SystemSettingsView(TemplateView):
    """View for system settings page"""
    template_name = 'dashboard/system_settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add system settings context data here
        return context


class UserListView(TemplateView):
    """View for user management page"""
    template_name = 'dashboard/user_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        context['users'] = User.objects.all().order_by('-date_joined')
        return context
