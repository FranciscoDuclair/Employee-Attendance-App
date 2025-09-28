from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Shift, ShiftTemplate, ShiftSchedule


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    """Admin interface for Shift model"""
    list_display = [
        'name', 'start_time', 'end_time', 'break_duration', 
        'duration_hours', 'total_hours', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'start_time', 'end_time', 'created_at']
    search_fields = ['name']
    ordering = ['name', 'start_time']
    readonly_fields = ['duration_hours', 'total_hours', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'start_time', 'end_time', 'break_duration')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_hours(self, obj):
        """Display duration in hours"""
        return f"{obj.duration_hours:.2f} hours"
    duration_hours.short_description = 'Duration (Hours)'
    
    def total_hours(self, obj):
        """Display total working hours"""
        return f"{obj.total_hours:.2f} hours"
    total_hours.short_description = 'Working Hours'


@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    """Admin interface for ShiftTemplate model"""
    list_display = [
        'name', 'shift', 'frequency', 'start_date', 'end_date', 
        'is_active', 'created_by', 'created_at'
    ]
    list_filter = ['frequency', 'is_active', 'start_date', 'end_date', 'created_at']
    search_fields = ['name', 'shift__name']
    ordering = ['-created_at']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'shift', 'frequency')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ShiftSchedule)
class ShiftScheduleAdmin(admin.ModelAdmin):
    """Admin interface for ShiftSchedule model"""
    list_display = [
        'employee', 'shift', 'date', 'status', 'template', 
        'is_today', 'is_overdue', 'created_by', 'created_at'
    ]
    list_filter = [
        'status', 'date', 'shift', 'template', 'created_at'
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 
        'shift__name', 'notes'
    ]
    ordering = ['-date', 'shift__start_time']
    readonly_fields = [
        'created_by', 'created_at', 'updated_at',
        'is_today', 'is_overdue', 'can_start', 'can_end'
    ]
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('employee', 'shift', 'date', 'status')
        }),
        ('Template & Notes', {
            'fields': ('template', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Computed Properties', {
            'fields': ('is_today', 'is_overdue', 'can_start', 'can_end'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_completed', 'mark_cancelled', 'mark_no_show']
    
    def is_today(self, obj):
        """Display if shift is today"""
        if obj.is_today:
            return format_html('<span style="color: green;">✓ Today</span>')
        return format_html('<span style="color: gray;">-</span>')
    is_today.short_description = 'Today'
    
    def is_overdue(self, obj):
        """Display if shift is overdue"""
        if obj.is_overdue:
            return format_html('<span style="color: red;">⚠ Overdue</span>')
        return format_html('<span style="color: gray;">-</span>')
    is_overdue.short_description = 'Overdue'
    
    def can_start(self, obj):
        """Display if shift can be started"""
        if obj.can_start:
            return format_html('<span style="color: blue;">✓ Can Start</span>')
        return format_html('<span style="color: gray;">-</span>')
    can_start.short_description = 'Can Start'
    
    def can_end(self, obj):
        """Display if shift can be ended"""
        if obj.can_end:
            return format_html('<span style="color: orange;">✓ Can End</span>')
        return format_html('<span style="color: gray;">-</span>')
    can_end.short_description = 'Can End'
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def mark_completed(self, request, queryset):
        """Mark selected shifts as completed"""
        updated = queryset.update(status='completed')
        self.message_user(
            request, 
            f'Successfully marked {updated} shift(s) as completed.'
        )
    mark_completed.short_description = 'Mark selected shifts as completed'
    
    def mark_cancelled(self, request, queryset):
        """Mark selected shifts as cancelled"""
        updated = queryset.update(status='cancelled')
        self.message_user(
            request, 
            f'Successfully marked {updated} shift(s) as cancelled.'
        )
    mark_cancelled.short_description = 'Mark selected shifts as cancelled'
    
    def mark_no_show(self, request, queryset):
        """Mark selected shifts as no show"""
        updated = queryset.update(status='no_show')
        self.message_user(
            request, 
            f'Successfully marked {updated} shift(s) as no show.'
        )
    mark_no_show.short_description = 'Mark selected shifts as no show'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'employee', 'shift', 'template', 'created_by'
        )
