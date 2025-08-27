from django.contrib import admin
from django.utils.html import format_html
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """Admin interface for Attendance model"""
    
    list_display = [
        'user', 'date', 'attendance_type', 'status', 'face_verified',
        'is_manual', 'hours_worked', 'created_at'
    ]
    list_filter = [
        'date', 'attendance_type', 'status', 'face_verified',
        'is_manual', 'user__role', 'user__department'
    ]
    search_fields = [
        'user__first_name', 'user__last_name', 'user__employee_id',
        'user__email'
    ]
    ordering = ['-date', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'date', 'attendance_type', 'status')
        }),
        ('Timing', {
            'fields': ('check_in_time', 'check_out_time')
        }),
        ('Face Recognition', {
            'fields': ('face_verified', 'face_confidence'),
            'classes': ('collapse',)
        }),
        ('Manual Override', {
            'fields': ('is_manual', 'manual_approved_by', 'manual_reason'),
            'classes': ('collapse',)
        }),
        ('Location & Notes', {
            'fields': ('latitude', 'longitude', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'hours_worked']
    
    def hours_worked(self, obj):
        """Display hours worked"""
        if obj.hours_worked > 0:
            return f"{obj.hours_worked:.2f} hours"
        return "N/A"
    hours_worked.short_description = 'Hours Worked'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'manual_approved_by')
    
    actions = ['approve_attendance', 'reject_attendance']
    
    def approve_attendance(self, request, queryset):
        """Approve selected attendance records"""
        updated = queryset.update(status='present')
        self.message_user(request, f'{updated} attendance records approved successfully.')
    approve_attendance.short_description = "Approve selected attendance records"
    
    def reject_attendance(self, request, queryset):
        """Reject selected attendance records"""
        updated = queryset.update(status='absent')
        self.message_user(request, f'{updated} attendance records rejected successfully.')
    reject_attendance.short_description = "Reject selected attendance records"
