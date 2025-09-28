from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Attendance, AttendanceSettings


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """Admin interface for Attendance model"""
    
    list_display = [
        'user', 'employee_id', 'date', 'attendance_type', 'status',
        'check_in_time', 'check_out_time', 'hours_worked',
        'face_verified_display', 'face_confidence_display', 'location_display'
    ]
    
    list_filter = [
        'attendance_type', 'status', 'face_verified', 'date',
        'user__department', 'user__role'
    ]
    
    search_fields = [
        'user__username', 'user__email', 'user__employee_id',
        'user__first_name', 'user__last_name'
    ]
    
    readonly_fields = [
        'hours_worked', 'is_late', 'is_face_verified', 'location_string',
        'created_at', 'updated_at', 'face_image_preview'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'date', 'attendance_type', 'status')
        }),
        ('Time Tracking', {
            'fields': ('check_in_time', 'check_out_time', 'hours_worked', 'is_late')
        }),
        ('Face Recognition', {
            'fields': ('face_verified', 'face_confidence', 'face_image', 'face_image_preview', 'is_face_verified'),
            'classes': ('collapse',)
        }),
        ('Location Data', {
            'fields': ('latitude', 'longitude', 'location_accuracy', 'location_string'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'ip_address', 'device_info'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'date'
    ordering = ['-date', '-created_at']
    
    def employee_id(self, obj):
        """Display employee ID"""
        return obj.user.employee_id
    employee_id.short_description = 'Employee ID'
    employee_id.admin_order_field = 'user__employee_id'
    
    def face_verified_display(self, obj):
        """Display face verification status with icon"""
        if obj.face_verified:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Not Verified</span>'
            )
    face_verified_display.short_description = 'Face Verified'
    face_verified_display.admin_order_field = 'face_verified'
    
    def face_confidence_display(self, obj):
        """Display face confidence with color coding"""
        if obj.face_confidence is not None:
            confidence = obj.face_confidence
            if confidence >= 0.8:
                color = 'green'
            elif confidence >= 0.6:
                color = 'orange'
            else:
                color = 'red'
            
            return format_html(
                '<span style="color: {};">{:.1%}</span>',
                color, confidence
            )
        return '-'
    face_confidence_display.short_description = 'Confidence'
    face_confidence_display.admin_order_field = 'face_confidence'
    
    def location_display(self, obj):
        """Display location with link to maps if available"""
        if obj.latitude and obj.longitude:
            maps_url = f"https://www.google.com/maps?q={obj.latitude},{obj.longitude}"
            return format_html(
                '<a href="{}" target="_blank">📍 View</a>',
                maps_url
            )
        return '-'
    location_display.short_description = 'Location'
    
    def face_image_preview(self, obj):
        """Display face image preview"""
        if obj.face_image:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 100px;" />',
                obj.face_image.url
            )
        return 'No image'
    face_image_preview.short_description = 'Face Image Preview'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        """Restrict manual attendance creation"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Allow changes for HR and admins"""
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role') and request.user.role in ['hr', 'manager']:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Restrict deletion to superusers only"""
        return request.user.is_superuser
    
    actions = ['mark_as_present', 'mark_as_late', 'export_to_csv']
    
    def mark_as_present(self, request, queryset):
        """Mark selected attendance records as present"""
        updated = queryset.update(status='present')
        self.message_user(request, f'{updated} records marked as present.')
    mark_as_present.short_description = 'Mark selected as present'
    
    def mark_as_late(self, request, queryset):
        """Mark selected attendance records as late"""
        updated = queryset.update(status='late')
        self.message_user(request, f'{updated} records marked as late.')
    mark_as_late.short_description = 'Mark selected as late'
    
    def export_to_csv(self, request, queryset):
        """Export selected records to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Name', 'Date', 'Type', 'Status',
            'Check In', 'Check Out', 'Hours', 'Face Verified', 'Confidence'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.user.employee_id,
                obj.user.get_full_name(),
                obj.date,
                obj.get_attendance_type_display(),
                obj.get_status_display(),
                obj.check_in_time.strftime('%H:%M:%S') if obj.check_in_time else '',
                obj.check_out_time.strftime('%H:%M:%S') if obj.check_out_time else '',
                obj.hours_worked or '',
                'Yes' if obj.face_verified else 'No',
                f'{obj.face_confidence:.1%}' if obj.face_confidence else ''
            ])
        
        return response
    export_to_csv.short_description = 'Export selected to CSV'


@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    """Admin interface for Attendance Settings"""
    
    fieldsets = (
        ('Face Recognition Settings', {
            'fields': ('face_recognition_enabled', 'face_confidence_threshold'),
            'description': 'Configure face recognition parameters'
        }),
        ('Location Settings', {
            'fields': (
                'location_tracking_enabled', 'location_radius_meters',
                'office_latitude', 'office_longitude'
            ),
            'description': 'Configure location-based attendance tracking'
        }),
        ('Time Settings', {
            'fields': ('late_threshold_minutes', 'early_departure_threshold_minutes'),
            'description': 'Configure time-based attendance rules'
        }),
        ('System Settings', {
            'fields': ('require_photo_for_attendance', 'allow_manual_attendance'),
            'description': 'General system behavior settings'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """Only allow one settings instance"""
        return not AttendanceSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings"""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Redirect to change view if settings exist"""
        if AttendanceSettings.objects.exists():
            settings = AttendanceSettings.objects.first()
            return self.change_view(request, str(settings.pk), extra_context)
        return super().changelist_view(request, extra_context)


# Custom admin site configuration
admin.site.site_header = "Employee Attendance Platform"
admin.site.site_title = "Attendance Admin"
admin.site.index_title = "Welcome to Attendance Administration"
