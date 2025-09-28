from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F, Case, When, IntegerField
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters
from datetime import datetime, timedelta
from django.http import HttpResponse, FileResponse
import csv
import json
from io import StringIO, BytesIO
from decimal import Decimal

from .models import ReportTemplate, ReportExecution, Dashboard, AnalyticsMetric
from .serializers import (
    ReportTemplateSerializer, ReportTemplateCreateSerializer,
    ReportExecutionSerializer, ReportExecutionCreateSerializer,
    DashboardSerializer, DashboardCreateSerializer,
    AnalyticsMetricSerializer, AttendanceReportSerializer,
    LeaveReportSerializer, PayrollReportSerializer, ShiftReportSerializer,
    DashboardDataSerializer, AnalyticsDataSerializer
)
from users.models import User
from attendance.models import Attendance
from leave.models import LeaveRequest, LeaveBalance
from payroll.models import Payroll
from shifts.models import ShiftSchedule
from .utils import (
    generate_pdf_report, generate_csv_report, calculate_analytics_metrics,
    create_dashboard_widgets, export_report_data
)


# Report Templates Management
class ReportTemplateListView(generics.ListCreateAPIView):
    """List and create report templates"""
    queryset = ReportTemplate.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'format_type', 'is_public'] if DjangoFilterBackend else []
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'report_type']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReportTemplateCreateSerializer
        return ReportTemplateSerializer

    def get_queryset(self):
        """Filter templates based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.role in ['hr', 'manager']:
            return queryset
        else:
            # Regular employees see public templates only
            return queryset.filter(Q(is_public=True) | Q(created_by=user))

    def perform_create(self, serializer):
        """Set creator and validate permissions"""
        user = self.request.user
        if user.role not in ['hr', 'manager']:
            # Regular employees can only create personal templates
            serializer.save(created_by=user, is_public=False)
        else:
            serializer.save(created_by=user)


class ReportTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete report template"""
    queryset = ReportTemplate.objects.filter(is_active=True)
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.role in ['hr', 'manager']:
            return queryset
        else:
            return queryset.filter(Q(is_public=True) | Q(created_by=user))


# Report Execution Management
class ReportExecutionListView(generics.ListCreateAPIView):
    """List and create report executions"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'report_type', 'format_type'] if DjangoFilterBackend else []
    search_fields = ['name']
    ordering_fields = ['created_at', 'completed_at', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReportExecutionCreateSerializer
        return ReportExecutionSerializer

    def get_queryset(self):
        """Return user's report executions"""
        user = self.request.user
        queryset = ReportExecution.objects.all()
        
        if user.role in ['hr', 'manager']:
            return queryset
        else:
            return queryset.filter(Q(requested_by=user) | Q(is_public=True))

    def perform_create(self, serializer):
        """Create and execute report"""
        user = self.request.user
        execution = serializer.save(requested_by=user)
        
        # Execute report asynchronously (for now, execute immediately)
        self.execute_report(execution)

    def execute_report(self, execution):
        """Execute the report generation"""
        try:
            execution.status = 'processing'
            execution.started_at = timezone.now()
            execution.save()

            # Generate report based on type
            if execution.report_type == 'attendance':
                data = self.generate_attendance_report(execution)
            elif execution.report_type == 'leave':
                data = self.generate_leave_report(execution)
            elif execution.report_type == 'payroll':
                data = self.generate_payroll_report(execution)
            elif execution.report_type == 'shift':
                data = self.generate_shift_report(execution)
            else:
                raise ValueError(f"Unknown report type: {execution.report_type}")

            # Export data to file
            file_path = export_report_data(data, execution)
            
            execution.status = 'completed'
            execution.completed_at = timezone.now()
            execution.file_path = file_path
            execution.record_count = len(data) if isinstance(data, list) else 1
            execution.generation_time = execution.completed_at - execution.started_at
            execution.save()

        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()

    def generate_attendance_report(self, execution):
        """Generate attendance report data"""
        params = execution.parameters
        filters = execution.filters
        
        queryset = Attendance.objects.all()
        
        # Apply filters
        if filters.get('start_date'):
            queryset = queryset.filter(date__gte=filters['start_date'])
        if filters.get('end_date'):
            queryset = queryset.filter(date__lte=filters['end_date'])
        if filters.get('department'):
            queryset = queryset.filter(user__department=filters['department'])
        if filters.get('employee'):
            queryset = queryset.filter(user_id=filters['employee'])
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])

        return list(queryset.values(
            'id', 'user__first_name', 'user__last_name', 'user__employee_id',
            'date', 'check_in_time', 'check_out_time', 'status', 'hours_worked',
            'overtime_hours', 'attendance_type', 'notes'
        ))

    def generate_leave_report(self, execution):
        """Generate leave report data"""
        filters = execution.filters
        
        queryset = LeaveRequest.objects.all()
        
        # Apply filters
        if filters.get('start_date'):
            queryset = queryset.filter(start_date__gte=filters['start_date'])
        if filters.get('end_date'):
            queryset = queryset.filter(end_date__lte=filters['end_date'])
        if filters.get('department'):
            queryset = queryset.filter(user__department=filters['department'])
        if filters.get('employee'):
            queryset = queryset.filter(user_id=filters['employee'])
        if filters.get('leave_type'):
            queryset = queryset.filter(leave_type_id=filters['leave_type'])
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])

        return list(queryset.values(
            'id', 'user__first_name', 'user__last_name', 'user__employee_id',
            'leave_type__name', 'start_date', 'end_date', 'total_days',
            'status', 'reason', 'approved_by__first_name', 'approved_by__last_name',
            'approved_at', 'created_at'
        ))

    def generate_payroll_report(self, execution):
        """Generate payroll report data"""
        filters = execution.filters
        
        queryset = Payroll.objects.all()
        
        # Apply filters
        if filters.get('month'):
            queryset = queryset.filter(month=filters['month'])
        if filters.get('year'):
            queryset = queryset.filter(year=filters['year'])
        if filters.get('department'):
            queryset = queryset.filter(user__department=filters['department'])
        if filters.get('employee'):
            queryset = queryset.filter(user_id=filters['employee'])
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])

        return list(queryset.values(
            'id', 'user__first_name', 'user__last_name', 'user__employee_id',
            'month', 'year', 'basic_salary', 'overtime_pay', 'bonus',
            'deductions', 'gross_pay', 'tax_deduction', 'net_pay',
            'status', 'generated_at'
        ))

    def generate_shift_report(self, execution):
        """Generate shift report data"""
        filters = execution.filters
        
        queryset = ShiftSchedule.objects.all()
        
        # Apply filters
        if filters.get('start_date'):
            queryset = queryset.filter(date__gte=filters['start_date'])
        if filters.get('end_date'):
            queryset = queryset.filter(date__lte=filters['end_date'])
        if filters.get('department'):
            queryset = queryset.filter(employee__department=filters['department'])
        if filters.get('employee'):
            queryset = queryset.filter(employee_id=filters['employee'])
        if filters.get('shift'):
            queryset = queryset.filter(shift_id=filters['shift'])
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])

        return list(queryset.values(
            'id', 'employee__first_name', 'employee__last_name', 'employee__employee_id',
            'shift__name', 'date', 'shift__start_time', 'shift__end_time',
            'status', 'notes', 'created_by__first_name', 'created_by__last_name',
            'created_at'
        ))


class ReportExecutionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete report execution"""
    serializer_class = ReportExecutionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter based on user permissions"""
        user = self.request.user
        queryset = ReportExecution.objects.all()
        
        if user.role in ['hr', 'manager']:
            return queryset
        else:
            return queryset.filter(Q(requested_by=user) | Q(is_public=True))


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_report(request, execution_id):
    """Download generated report file"""
    try:
        execution = ReportExecution.objects.get(id=execution_id)
        
        # Check permissions
        user = request.user
        if user.role not in ['hr', 'manager'] and execution.requested_by != user and not execution.is_public:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if execution.status != 'completed':
            return Response({'error': 'Report not ready'}, status=status.HTTP_400_BAD_REQUEST)
        
        if execution.is_expired:
            return Response({'error': 'Report has expired'}, status=status.HTTP_410_GONE)
        
        # Mark as downloaded
        execution.mark_as_downloaded()
        
        # Return file response
        return FileResponse(
            open(execution.file_path, 'rb'),
            as_attachment=True,
            filename=f"{execution.name}.{execution.format_type}"
        )
        
    except ReportExecution.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)


# Quick Report Generation
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_attendance_report(request):
    """Generate attendance report directly"""
    serializer = AttendanceReportSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        # Query attendance data
        queryset = Attendance.objects.filter(
            date__range=[data['start_date'], data['end_date']]
        )
        
        # Apply filters
        if data.get('department'):
            queryset = queryset.filter(user__department=data['department'])
        if data.get('employee'):
            queryset = queryset.filter(user_id=data['employee'])
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        
        # Generate response based on format
        if data['format'] == 'csv':
            return generate_csv_response(queryset, 'attendance_report')
        elif data['format'] == 'json':
            return Response({
                'data': list(queryset.values(
                    'user__first_name', 'user__last_name', 'date',
                    'check_in_time', 'check_out_time', 'status', 'hours_worked'
                )),
                'count': queryset.count()
            })
        else:
            # PDF format
            return generate_pdf_response(queryset, 'attendance_report')
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_leave_report(request):
    """Generate leave report directly"""
    serializer = LeaveReportSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data
        
        # Query leave data
        queryset = LeaveRequest.objects.filter(
            start_date__range=[data['start_date'], data['end_date']]
        )
        
        # Apply filters
        if data.get('department'):
            queryset = queryset.filter(user__department=data['department'])
        if data.get('employee'):
            queryset = queryset.filter(user_id=data['employee'])
        if data.get('leave_type'):
            queryset = queryset.filter(leave_type_id=data['leave_type'])
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        
        # Generate response based on format
        if data['format'] == 'csv':
            return generate_csv_response(queryset, 'leave_report')
        elif data['format'] == 'json':
            return Response({
                'data': list(queryset.values(
                    'user__first_name', 'user__last_name', 'leave_type__name',
                    'start_date', 'end_date', 'total_days', 'status', 'reason'
                )),
                'count': queryset.count()
            })
        else:
            return generate_pdf_response(queryset, 'leave_report')
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Dashboard Management
class DashboardListView(generics.ListCreateAPIView):
    """List and create dashboards"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter] if DjangoFilterBackend else [filters.SearchFilter]
    filterset_fields = ['dashboard_type', 'is_public'] if DjangoFilterBackend else []
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return DashboardCreateSerializer
        return DashboardSerializer

    def get_queryset(self):
        """Filter dashboards based on user permissions"""
        user = self.request.user
        queryset = Dashboard.objects.filter(is_active=True)
        
        if user.role in ['hr', 'manager']:
            return queryset
        else:
            return queryset.filter(Q(is_public=True) | Q(created_by=user))

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_data(request, dashboard_id):
    """Get dashboard data with all widgets"""
    try:
        dashboard = Dashboard.objects.get(id=dashboard_id, is_active=True)
        
        # Check permissions
        user = request.user
        if user.role not in ['hr', 'manager'] and dashboard.created_by != user and not dashboard.is_public:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Generate widget data
        widgets_data = []
        for widget_config in dashboard.widgets:
            widget_data = create_dashboard_widgets(widget_config, user)
            widgets_data.append(widget_data)
        
        return Response({
            'dashboard': DashboardSerializer(dashboard).data,
            'widgets': widgets_data,
            'last_updated': timezone.now()
        })
        
    except Dashboard.DoesNotExist:
        return Response({'error': 'Dashboard not found'}, status=status.HTTP_404_NOT_FOUND)


# Analytics & Metrics
class AnalyticsMetricListView(generics.ListCreateAPIView):
    """List and create analytics metrics"""
    queryset = AnalyticsMetric.objects.filter(is_active=True)
    serializer_class = AnalyticsMetricSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter] if DjangoFilterBackend else [filters.SearchFilter]
    filterset_fields = ['metric_type', 'update_frequency'] if DjangoFilterBackend else []
    search_fields = ['name', 'description']


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def analytics_data(request):
    """Get analytics data for dashboard"""
    serializer = AnalyticsDataSerializer(data=request.query_params)
    if serializer.is_valid():
        data = serializer.validated_data
        
        # Calculate analytics metrics
        analytics = calculate_analytics_metrics(data)
        
        return Response(analytics)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def attendance_analytics(request):
    """Get attendance analytics"""
    # Get date range (default to current month)
    end_date = timezone.now().date()
    start_date = end_date.replace(day=1)
    
    if request.query_params.get('start_date'):
        start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
    if request.query_params.get('end_date'):
        end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
    
    # Calculate metrics
    total_days = (end_date - start_date).days + 1
    attendance_data = Attendance.objects.filter(date__range=[start_date, end_date])
    
    # Attendance rate by status
    status_counts = attendance_data.values('status').annotate(count=Count('id'))
    
    # Daily attendance trends
    daily_trends = attendance_data.values('date').annotate(
        present=Count(Case(When(status='present', then=1), output_field=IntegerField())),
        late=Count(Case(When(status='late', then=1), output_field=IntegerField())),
        absent=Count(Case(When(status='absent', then=1), output_field=IntegerField()))
    ).order_by('date')
    
    # Department-wise attendance
    dept_attendance = attendance_data.values('user__department').annotate(
        total=Count('id'),
        present=Count(Case(When(status='present', then=1), output_field=IntegerField()))
    )
    
    return Response({
        'period': {'start_date': start_date, 'end_date': end_date, 'total_days': total_days},
        'status_summary': list(status_counts),
        'daily_trends': list(daily_trends),
        'department_summary': list(dept_attendance),
        'total_records': attendance_data.count()
    })


# Helper functions
def generate_csv_response(queryset, filename):
    """Generate CSV response from queryset"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    
    # Write headers (based on queryset model)
    if queryset.model == Attendance:
        writer.writerow(['Employee', 'Date', 'Check In', 'Check Out', 'Status', 'Hours Worked'])
        for record in queryset:
            writer.writerow([
                f"{record.user.first_name} {record.user.last_name}",
                record.date,
                record.check_in_time,
                record.check_out_time,
                record.status,
                record.hours_worked
            ])
    elif queryset.model == LeaveRequest:
        writer.writerow(['Employee', 'Leave Type', 'Start Date', 'End Date', 'Days', 'Status', 'Reason'])
        for record in queryset:
            writer.writerow([
                f"{record.user.first_name} {record.user.last_name}",
                record.leave_type.name,
                record.start_date,
                record.end_date,
                record.total_days,
                record.status,
                record.reason
            ])
    
    return response


def generate_pdf_response(queryset, filename):
    """Generate PDF response from queryset"""
    # This would use a library like ReportLab
    # For now, return a placeholder response
    return Response({
        'message': 'PDF generation not implemented yet',
        'data_count': queryset.count(),
        'filename': f"{filename}.pdf"
    })


@login_required
def team_analytics_web(request):
    """Web-based team analytics view for managers"""
    user = request.user
    
    # Check if user can manage team analytics
    if not user.can_manage_attendance():
        return render(request, 'reports/access_denied.html')
    
    # Get date range parameters
    end_date = timezone.now().date()
    start_date = end_date.replace(day=1)  # Start of current month
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Get team members
    from users.models import User
    team_members = User.objects.filter(manager=user)
    
    # Get attendance data for the period
    attendance_data = Attendance.objects.filter(
        user__in=team_members,
        date__range=[start_date, end_date]
    ).select_related('user')
    
    # Calculate analytics
    total_days = (end_date - start_date).days + 1
    
    # Status summary
    status_counts = attendance_data.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Daily trends
    daily_trends = attendance_data.values('date').annotate(
        total=Count('id'),
        present=Count(Case(When(status='present', then=1), output_field=IntegerField())),
        absent=Count(Case(When(status='absent', then=1), output_field=IntegerField()))
    ).order_by('date')
    
    # Department-wise attendance (if departments exist)
    dept_attendance = attendance_data.values('user__department').annotate(
        total=Count('id'),
        present=Count(Case(When(status='present', then=1), output_field=IntegerField()))
    )
    
    # Employee performance
    employee_stats = attendance_data.values('user__id', 'user__first_name', 'user__last_name').annotate(
        total_days=Count('id'),
        present_days=Count(Case(When(status='present', then=1), output_field=IntegerField())),
        absent_days=Count(Case(When(status='absent', then=1), output_field=IntegerField())),
        late_days=Count(Case(When(status='late', then=1), output_field=IntegerField()))
    ).order_by('-present_days')
    
    # Calculate attendance rate for each employee
    for emp in employee_stats:
        if emp['total_days'] > 0:
            emp['attendance_rate'] = round((emp['present_days'] / emp['total_days']) * 100, 1)
        else:
            emp['attendance_rate'] = 0
    
    # Overall statistics
    total_records = attendance_data.count()
    present_count = attendance_data.filter(status='present').count()
    overall_attendance_rate = round((present_count / total_records * 100), 1) if total_records > 0 else 0
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_days': total_days,
        'team_members': team_members,
        'status_counts': status_counts,
        'daily_trends': daily_trends,
        'dept_attendance': dept_attendance,
        'employee_stats': employee_stats,
        'total_records': total_records,
        'overall_attendance_rate': overall_attendance_rate,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'reports/team_analytics.html', context)


@login_required
def generate_team_report_web(request):
    """Web-based team report generation view for managers"""
    user = request.user
    
    # Check if user can generate team reports
    if not user.can_manage_attendance():
        return render(request, 'reports/access_denied.html')
    
    if request.method == 'POST':
        # Get form parameters
        report_type = request.POST.get('report_type', 'attendance')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        format_type = request.POST.get('format_type', 'csv')
        employee_filter = request.POST.get('employee')
        
        # Get team members
        from users.models import User
        team_members = User.objects.filter(manager=user)
        
        # Build queryset based on report type
        if report_type == 'attendance':
            queryset = Attendance.objects.filter(user__in=team_members)
            if date_from:
                queryset = queryset.filter(date__gte=date_from)
            if date_to:
                queryset = queryset.filter(date__lte=date_to)
            if employee_filter:
                queryset = queryset.filter(user_id=employee_filter)
            
            queryset = queryset.select_related('user').order_by('-date', 'user__first_name')
            
            # Generate CSV response
            if format_type == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="attendance_report_{date_from}_{date_to}.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['Employee', 'Employee ID', 'Date', 'Check In', 'Check Out', 'Status', 'Hours Worked', 'Department'])
                
                for record in queryset:
                    writer.writerow([
                        f"{record.user.first_name} {record.user.last_name}",
                        record.user.employee_id or '',
                        record.date,
                        record.check_in_time or '',
                        record.check_out_time or '',
                        record.status,
                        record.hours_worked or 0,
                        record.user.department or ''
                    ])
                
                return response
        
        elif report_type == 'leave':
            queryset = LeaveRequest.objects.filter(user__in=team_members)
            if date_from:
                queryset = queryset.filter(start_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(end_date__lte=date_to)
            if employee_filter:
                queryset = queryset.filter(user_id=employee_filter)
            
            queryset = queryset.select_related('user', 'leave_type').order_by('-start_date')
            
            # Generate CSV response
            if format_type == 'csv':
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="leave_report_{date_from}_{date_to}.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['Employee', 'Employee ID', 'Leave Type', 'Start Date', 'End Date', 'Days', 'Status', 'Reason'])
                
                for record in queryset:
                    writer.writerow([
                        f"{record.user.first_name} {record.user.last_name}",
                        record.user.employee_id or '',
                        record.leave_type.name,
                        record.start_date,
                        record.end_date,
                        record.total_days,
                        record.status,
                        record.reason
                    ])
                
                return response
        
        messages.success(request, 'Report generated successfully!')
    
    # Get team members for form
    from users.models import User
    team_members = User.objects.filter(manager=user)
    
    context = {
        'team_members': team_members,
        'today': timezone.now().date(),
    }
    
    return render(request, 'reports/generate_report.html', context)
