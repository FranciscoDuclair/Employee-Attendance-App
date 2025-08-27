from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin interface"""
    
    list_display = [
        'employee_id', 'get_full_name', 'email', 'role', 'department',
        'position', 'is_active', 'date_joined'
    ]
    list_filter = ['role', 'department', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email']
    ordering = ['employee_id']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'employee_id', 'phone_number',
                'profile_picture'
            )
        }),
        ('Work info', {
            'fields': ('role', 'department', 'position', 'hire_date', 'manager')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Face Recognition', {'fields': ('face_encoding',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'employee_id', 'first_name', 'last_name',
                'role', 'password1', 'password2'
            ),
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Full Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('manager')
