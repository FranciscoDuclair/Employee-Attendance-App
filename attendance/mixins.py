from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages


class RoleRequiredMixin(UserPassesTestMixin):
    """Mixin to check if user has the required role(s)"""
    roles_required = []
    login_url = 'attendance_web:login'
    permission_denied_message = "You don't have permission to access this page."
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
            
        if not self.roles_required:  # If no roles specified, any authenticated user can access
            return True
            
        return self.request.user.role in self.roles_required
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
            
        messages.error(self.request, self.permission_denied_message)
        return redirect('attendance_web:dashboard')


class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin to restrict access to admin users only"""
    roles_required = ['hr']
    permission_denied_message = "This section is restricted to administrators only."


class ManagerRequiredMixin(RoleRequiredMixin):
    """Mixin to restrict access to managers and admins"""
    roles_required = ['hr', 'manager']
    permission_denied_message = "This section is restricted to managers and administrators only."


class EmployeeRequiredMixin(RoleRequiredMixin):
    """Mixin to restrict access to employees only"""
    roles_required = ['employee']
    permission_denied_message = "This section is for employees only."


def role_required(roles=None, login_url=None, message=None):
    """
    Decorator for function-based views to check user role.
    Usage: @role_required(['hr', 'manager'])
    """
    if not roles:
        roles = []
    
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path(), login_url)
                
            if roles and request.user.role not in roles:
                from django.contrib import messages
                from django.shortcuts import redirect
                
                messages.error(request, message or "You don't have permission to access this page.")
                return redirect(login_url or 'attendance_web:dashboard')
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
