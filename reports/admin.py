from django.contrib import admin
from .models import ReportTemplate, ReportExecution, Dashboard, AnalyticsMetric


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'format_type', 'is_public', 'created_by', 'created_at', 'is_active']
    list_filter = ['report_type', 'format_type', 'is_public', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'report_type', 'format_type')
        }),
        ('Configuration', {
            'fields': ('fields', 'filters', 'grouping', 'sorting')
        }),
        ('Access Control', {
            'fields': ('is_public', 'allowed_roles', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'format_type', 'status', 'requested_by', 'created_at', 'completed_at']
    list_filter = ['status', 'report_type', 'format_type', 'created_at']
    search_fields = ['name', 'requested_by__username']
    readonly_fields = ['created_at', 'updated_at', 'generation_time', 'download_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('template', 'name', 'report_type', 'format_type')
        }),
        ('Parameters', {
            'fields': ('parameters', 'filters')
        }),
        ('Execution Details', {
            'fields': ('status', 'started_at', 'completed_at', 'error_message', 'generation_time')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size', 'download_count', 'record_count')
        }),
        ('Access Control', {
            'fields': ('requested_by', 'is_public', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'dashboard_type', 'is_default', 'is_public', 'created_by', 'created_at', 'is_active']
    list_filter = ['dashboard_type', 'is_default', 'is_public', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'dashboard_type')
        }),
        ('Configuration', {
            'fields': ('widgets', 'layout', 'refresh_interval')
        }),
        ('Access Control', {
            'fields': ('is_default', 'is_public', 'allowed_roles', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(AnalyticsMetric)
class AnalyticsMetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'metric_type', 'current_value', 'target_value', 'update_frequency', 'last_calculated', 'is_active']
    list_filter = ['metric_type', 'update_frequency', 'is_active', 'last_calculated']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_calculated', 'trend', 'target_achievement']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'metric_type', 'description')
        }),
        ('Calculation', {
            'fields': ('calculation_method', 'query')
        }),
        ('Values', {
            'fields': ('current_value', 'previous_value', 'target_value', 'unit')
        }),
        ('Settings', {
            'fields': ('data_source', 'update_frequency', 'is_active')
        }),
        ('Status', {
            'fields': ('last_calculated', 'trend', 'target_achievement'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
