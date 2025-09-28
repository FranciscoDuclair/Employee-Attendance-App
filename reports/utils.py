"""
Utility functions for reports and analytics
"""
import csv
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F, Case, When, IntegerField
from django.contrib.auth import get_user_model

from attendance.models import Attendance
from leave.models import LeaveRequest, LeaveBalance
from payroll.models import Payroll
from shifts.models import ShiftSchedule, Shift

User = get_user_model()


def generate_pdf_report(data, report_type, filename=None):
    """
    Generate PDF report from data
    Uses ReportLab or similar library
    """
    try:
        # Import ReportLab components
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        # Create PDF buffer
        buffer = BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        title = f"{report_type.replace('_', ' ').title()} Report"
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # Date range info
        date_info = f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        story.append(Paragraph(date_info, styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Convert data to table format
        if data and isinstance(data, list):
            # Get headers from first record
            if isinstance(data[0], dict):
                headers = list(data[0].keys())
                table_data = [headers]
                
                # Add data rows
                for record in data:
                    row = [str(record.get(header, '')) for header in headers]
                    table_data.append(row)
                
                # Create table
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
        else:
            story.append(Paragraph("No data available for this report.", styles['Normal']))
        
        # Summary info
        story.append(Spacer(1, 20))
        summary = f"Total records: {len(data) if data else 0}"
        story.append(Paragraph(summary, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Save to file
        if not filename:
            filename = f"{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        file_path = os.path.join(reports_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        buffer.close()
        return file_path
        
    except ImportError:
        # ReportLab not installed, create a simple text file
        return create_text_report(data, report_type, filename)


def generate_csv_report(data, report_type, filename=None):
    """
    Generate CSV report from data
    """
    if not filename:
        filename = f"{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    file_path = os.path.join(reports_dir, filename)
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        if data and isinstance(data, list) and isinstance(data[0], dict):
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for record in data:
                writer.writerow(record)
        else:
            writer = csv.writer(csvfile)
            writer.writerow(['No data available'])
    
    return file_path


def create_text_report(data, report_type, filename=None):
    """
    Create a simple text report (fallback when PDF libraries not available)
    """
    if not filename:
        filename = f"{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    file_path = os.path.join(reports_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"{report_type.replace('_', ' ').title()} Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if data:
            f.write(f"Total records: {len(data)}\n\n")
            
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    # Write as key-value pairs
                    for i, record in enumerate(data, 1):
                        f.write(f"Record {i}:\n")
                        for key, value in record.items():
                            f.write(f"  {key}: {value}\n")
                        f.write("\n")
                else:
                    # Write as simple list
                    for item in data:
                        f.write(f"{item}\n")
        else:
            f.write("No data available for this report.\n")
    
    return file_path


def export_report_data(data, execution):
    """
    Export report data to the specified format
    """
    filename = f"{execution.name}_{execution.id}"
    
    if execution.format_type == 'csv':
        return generate_csv_report(data, execution.report_type, f"{filename}.csv")
    elif execution.format_type == 'pdf':
        return generate_pdf_report(data, execution.report_type, f"{filename}.pdf")
    elif execution.format_type == 'json':
        return create_json_report(data, execution.report_type, f"{filename}.json")
    else:
        return create_text_report(data, execution.report_type, f"{filename}.txt")


def create_json_report(data, report_type, filename=None):
    """
    Create JSON report file
    """
    if not filename:
        filename = f"{report_type}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    file_path = os.path.join(reports_dir, filename)
    
    report_data = {
        'report_type': report_type,
        'generated_at': timezone.now().isoformat(),
        'total_records': len(data) if data else 0,
        'data': data or []
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    return file_path


def calculate_analytics_metrics(params):
    """
    Calculate various analytics metrics based on parameters
    """
    period = params.get('period', 'month')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    department = params.get('department')
    
    # Set default date range if not provided
    if not start_date or not end_date:
        end_date = timezone.now().date()
        if period == 'day':
            start_date = end_date
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date.replace(day=1)
        elif period == 'year':
            start_date = end_date.replace(month=1, day=1)
        else:
            start_date = end_date - timedelta(days=30)
    
    analytics = {
        'period': {
            'start_date': start_date,
            'end_date': end_date,
            'period_type': period
        },
        'attendance_metrics': calculate_attendance_metrics(start_date, end_date, department),
        'leave_metrics': calculate_leave_metrics(start_date, end_date, department),
        'payroll_metrics': calculate_payroll_metrics(start_date, end_date, department),
        'shift_metrics': calculate_shift_metrics(start_date, end_date, department),
        'employee_metrics': calculate_employee_metrics(start_date, end_date, department)
    }
    
    return analytics


def calculate_attendance_metrics(start_date, end_date, department=None):
    """Calculate attendance-related metrics"""
    queryset = Attendance.objects.filter(date__range=[start_date, end_date])
    if department:
        queryset = queryset.filter(user__department=department)
    
    total_records = queryset.count()
    
    if total_records == 0:
        return {'total_records': 0, 'message': 'No attendance data available'}
    
    # Status distribution
    status_counts = queryset.values('status').annotate(count=Count('id'))
    
    # Calculate rates
    present_count = queryset.filter(status='present').count()
    late_count = queryset.filter(status='late').count()
    absent_count = queryset.filter(status='absent').count()
    
    attendance_rate = (present_count + late_count) / total_records * 100 if total_records > 0 else 0
    punctuality_rate = present_count / total_records * 100 if total_records > 0 else 0
    
    # Average hours worked
    avg_hours = queryset.aggregate(avg_hours=Avg('hours_worked'))['avg_hours'] or 0
    total_hours = queryset.aggregate(total_hours=Sum('hours_worked'))['total_hours'] or 0
    total_overtime = queryset.aggregate(total_overtime=Sum('overtime_hours'))['total_overtime'] or 0
    
    # Daily trends
    daily_trends = queryset.values('date').annotate(
        total=Count('id'),
        present=Count(Case(When(status='present', then=1), output_field=IntegerField())),
        late=Count(Case(When(status='late', then=1), output_field=IntegerField())),
        absent=Count(Case(When(status='absent', then=1), output_field=IntegerField()))
    ).order_by('date')
    
    return {
        'total_records': total_records,
        'attendance_rate': round(attendance_rate, 2),
        'punctuality_rate': round(punctuality_rate, 2),
        'status_distribution': {
            'present': present_count,
            'late': late_count,
            'absent': absent_count
        },
        'hours_summary': {
            'average_hours': round(float(avg_hours), 2),
            'total_hours': round(float(total_hours), 2),
            'total_overtime': round(float(total_overtime), 2)
        },
        'daily_trends': list(daily_trends)
    }


def calculate_leave_metrics(start_date, end_date, department=None):
    """Calculate leave-related metrics"""
    queryset = LeaveRequest.objects.filter(
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    if department:
        queryset = queryset.filter(user__department=department)
    
    total_requests = queryset.count()
    
    if total_requests == 0:
        return {'total_requests': 0, 'message': 'No leave data available'}
    
    # Status distribution
    approved_count = queryset.filter(status='approved').count()
    pending_count = queryset.filter(status='pending').count()
    rejected_count = queryset.filter(status='rejected').count()
    
    approval_rate = approved_count / total_requests * 100 if total_requests > 0 else 0
    
    # Leave days analysis
    total_days = queryset.aggregate(total_days=Sum('total_days'))['total_days'] or 0
    avg_days = queryset.aggregate(avg_days=Avg('total_days'))['avg_days'] or 0
    
    # Leave type distribution
    leave_types = queryset.values('leave_type__name').annotate(
        count=Count('id'),
        total_days=Sum('total_days')
    )
    
    return {
        'total_requests': total_requests,
        'approval_rate': round(approval_rate, 2),
        'status_distribution': {
            'approved': approved_count,
            'pending': pending_count,
            'rejected': rejected_count
        },
        'days_summary': {
            'total_days': total_days,
            'average_days': round(float(avg_days), 2)
        },
        'leave_type_distribution': list(leave_types)
    }


def calculate_payroll_metrics(start_date, end_date, department=None):
    """Calculate payroll-related metrics"""
    # Get month/year from date range
    start_month = start_date.month
    start_year = start_date.year
    end_month = end_date.month
    end_year = end_date.year
    
    queryset = Payroll.objects.filter(
        year__range=[start_year, end_year]
    )
    
    if start_year == end_year:
        queryset = queryset.filter(month__range=[start_month, end_month])
    
    if department:
        queryset = queryset.filter(user__department=department)
    
    total_records = queryset.count()
    
    if total_records == 0:
        return {'total_records': 0, 'message': 'No payroll data available'}
    
    # Calculate totals
    totals = queryset.aggregate(
        total_gross=Sum('gross_pay'),
        total_net=Sum('net_pay'),
        total_tax=Sum('tax_deduction'),
        total_deductions=Sum('deductions'),
        avg_gross=Avg('gross_pay'),
        avg_net=Avg('net_pay')
    )
    
    # Status distribution
    status_counts = queryset.values('status').annotate(count=Count('id'))
    
    return {
        'total_records': total_records,
        'totals': {
            'gross_pay': round(float(totals['total_gross'] or 0), 2),
            'net_pay': round(float(totals['total_net'] or 0), 2),
            'tax_deductions': round(float(totals['total_tax'] or 0), 2),
            'other_deductions': round(float(totals['total_deductions'] or 0), 2)
        },
        'averages': {
            'gross_pay': round(float(totals['avg_gross'] or 0), 2),
            'net_pay': round(float(totals['avg_net'] or 0), 2)
        },
        'status_distribution': list(status_counts)
    }


def calculate_shift_metrics(start_date, end_date, department=None):
    """Calculate shift-related metrics"""
    queryset = ShiftSchedule.objects.filter(date__range=[start_date, end_date])
    if department:
        queryset = queryset.filter(employee__department=department)
    
    total_schedules = queryset.count()
    
    if total_schedules == 0:
        return {'total_schedules': 0, 'message': 'No shift data available'}
    
    # Status distribution
    completed_count = queryset.filter(status='completed').count()
    scheduled_count = queryset.filter(status='scheduled').count()
    cancelled_count = queryset.filter(status='cancelled').count()
    
    completion_rate = completed_count / total_schedules * 100 if total_schedules > 0 else 0
    
    # Shift distribution
    shift_distribution = queryset.values('shift__name').annotate(
        count=Count('id'),
        completed=Count(Case(When(status='completed', then=1), output_field=IntegerField()))
    )
    
    # Coverage analysis
    total_shifts = Shift.objects.filter(is_active=True).count()
    covered_shifts = queryset.filter(status__in=['scheduled', 'completed']).values('shift').distinct().count()
    coverage_rate = covered_shifts / total_shifts * 100 if total_shifts > 0 else 0
    
    return {
        'total_schedules': total_schedules,
        'completion_rate': round(completion_rate, 2),
        'coverage_rate': round(coverage_rate, 2),
        'status_distribution': {
            'completed': completed_count,
            'scheduled': scheduled_count,
            'cancelled': cancelled_count
        },
        'shift_distribution': list(shift_distribution)
    }


def calculate_employee_metrics(start_date, end_date, department=None):
    """Calculate employee-related metrics"""
    user_queryset = User.objects.filter(is_active=True)
    if department:
        user_queryset = user_queryset.filter(department=department)
    
    total_employees = user_queryset.count()
    
    # Active employees (those with recent attendance)
    active_employees = user_queryset.filter(
        attendance_records__date__range=[start_date, end_date]
    ).distinct().count()
    
    # Department distribution
    dept_distribution = user_queryset.values('department').annotate(
        count=Count('id')
    )
    
    # Role distribution
    role_distribution = user_queryset.values('role').annotate(
        count=Count('id')
    )
    
    return {
        'total_employees': total_employees,
        'active_employees': active_employees,
        'activity_rate': round(active_employees / total_employees * 100 if total_employees > 0 else 0, 2),
        'department_distribution': list(dept_distribution),
        'role_distribution': list(role_distribution)
    }


def create_dashboard_widgets(widget_config, user):
    """
    Create dashboard widget data based on configuration
    """
    widget_type = widget_config.get('type')
    widget_title = widget_config.get('title', 'Widget')
    widget_params = widget_config.get('params', {})
    
    if widget_type == 'attendance_summary':
        return create_attendance_summary_widget(widget_title, widget_params, user)
    elif widget_type == 'leave_summary':
        return create_leave_summary_widget(widget_title, widget_params, user)
    elif widget_type == 'payroll_summary':
        return create_payroll_summary_widget(widget_title, widget_params, user)
    elif widget_type == 'shift_summary':
        return create_shift_summary_widget(widget_title, widget_params, user)
    elif widget_type == 'chart':
        return create_chart_widget(widget_title, widget_params, user)
    else:
        return {
            'type': widget_type,
            'title': widget_title,
            'data': {'error': 'Unknown widget type'},
            'config': widget_config
        }


def create_attendance_summary_widget(title, params, user):
    """Create attendance summary widget"""
    # Get current month data
    today = timezone.now().date()
    start_date = today.replace(day=1)
    
    queryset = Attendance.objects.filter(
        date__range=[start_date, today]
    )
    
    # Filter by user role
    if user.role not in ['hr', 'manager']:
        queryset = queryset.filter(user=user)
    
    total = queryset.count()
    present = queryset.filter(status='present').count()
    late = queryset.filter(status='late').count()
    absent = queryset.filter(status='absent').count()
    
    attendance_rate = (present + late) / total * 100 if total > 0 else 0
    
    return {
        'type': 'attendance_summary',
        'title': title,
        'data': {
            'total': total,
            'present': present,
            'late': late,
            'absent': absent,
            'attendance_rate': round(attendance_rate, 1)
        },
        'config': params
    }


def create_leave_summary_widget(title, params, user):
    """Create leave summary widget"""
    queryset = LeaveRequest.objects.all()
    
    # Filter by user role
    if user.role not in ['hr', 'manager']:
        queryset = queryset.filter(user=user)
    
    # Current month
    today = timezone.now().date()
    current_month = queryset.filter(
        start_date__month=today.month,
        start_date__year=today.year
    )
    
    total = current_month.count()
    approved = current_month.filter(status='approved').count()
    pending = current_month.filter(status='pending').count()
    rejected = current_month.filter(status='rejected').count()
    
    return {
        'type': 'leave_summary',
        'title': title,
        'data': {
            'total': total,
            'approved': approved,
            'pending': pending,
            'rejected': rejected
        },
        'config': params
    }


def create_payroll_summary_widget(title, params, user):
    """Create payroll summary widget"""
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    
    queryset = Payroll.objects.filter(
        month=current_month,
        year=current_year
    )
    
    # Filter by user role
    if user.role not in ['hr', 'manager']:
        queryset = queryset.filter(user=user)
        if queryset.exists():
            payroll = queryset.first()
            return {
                'type': 'payroll_summary',
                'title': title,
                'data': {
                    'gross_pay': float(payroll.gross_pay),
                    'net_pay': float(payroll.net_pay),
                    'status': payroll.status
                },
                'config': params
            }
        else:
            return {
                'type': 'payroll_summary',
                'title': title,
                'data': {'message': 'No payroll data available'},
                'config': params
            }
    
    # HR/Manager view - summary of all payrolls
    totals = queryset.aggregate(
        total_gross=Sum('gross_pay'),
        total_net=Sum('net_pay'),
        count=Count('id')
    )
    
    return {
        'type': 'payroll_summary',
        'title': title,
        'data': {
            'total_employees': totals['count'] or 0,
            'total_gross': float(totals['total_gross'] or 0),
            'total_net': float(totals['total_net'] or 0)
        },
        'config': params
    }


def create_shift_summary_widget(title, params, user):
    """Create shift summary widget"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    queryset = ShiftSchedule.objects.filter(
        date__range=[week_start, week_end]
    )
    
    # Filter by user role
    if user.role not in ['hr', 'manager']:
        queryset = queryset.filter(employee=user)
    
    total = queryset.count()
    completed = queryset.filter(status='completed').count()
    scheduled = queryset.filter(status='scheduled').count()
    cancelled = queryset.filter(status='cancelled').count()
    
    return {
        'type': 'shift_summary',
        'title': title,
        'data': {
            'total': total,
            'completed': completed,
            'scheduled': scheduled,
            'cancelled': cancelled,
            'period': f"{week_start} to {week_end}"
        },
        'config': params
    }


def create_chart_widget(title, params, user):
    """Create chart widget with various chart types"""
    chart_type = params.get('chart_type', 'line')
    data_source = params.get('data_source', 'attendance')
    period = params.get('period', 'week')
    
    # Generate chart data based on source
    if data_source == 'attendance':
        chart_data = generate_attendance_chart_data(chart_type, period, user)
    elif data_source == 'leave':
        chart_data = generate_leave_chart_data(chart_type, period, user)
    else:
        chart_data = {'labels': [], 'datasets': []}
    
    return {
        'type': 'chart',
        'title': title,
        'data': chart_data,
        'config': {
            'chart_type': chart_type,
            'data_source': data_source,
            'period': period
        }
    }


def generate_attendance_chart_data(chart_type, period, user):
    """Generate chart data for attendance metrics"""
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
        date_range = [start_date + timedelta(days=i) for i in range(8)]
    elif period == 'month':
        start_date = today.replace(day=1)
        date_range = [start_date + timedelta(days=i) for i in range((today - start_date).days + 1)]
    else:
        start_date = today - timedelta(days=30)
        date_range = [start_date + timedelta(days=i) for i in range(31)]
    
    queryset = Attendance.objects.filter(
        date__range=[start_date, today]
    )
    
    # Filter by user role
    if user.role not in ['hr', 'manager']:
        queryset = queryset.filter(user=user)
    
    # Generate daily counts
    daily_data = {}
    for date in date_range:
        day_records = queryset.filter(date=date)
        daily_data[date.strftime('%Y-%m-%d')] = {
            'present': day_records.filter(status='present').count(),
            'late': day_records.filter(status='late').count(),
            'absent': day_records.filter(status='absent').count()
        }
    
    labels = list(daily_data.keys())
    
    if chart_type == 'line':
        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'Present',
                    'data': [daily_data[date]['present'] for date in labels],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)'
                },
                {
                    'label': 'Late',
                    'data': [daily_data[date]['late'] for date in labels],
                    'borderColor': 'rgb(255, 205, 86)',
                    'backgroundColor': 'rgba(255, 205, 86, 0.2)'
                },
                {
                    'label': 'Absent',
                    'data': [daily_data[date]['absent'] for date in labels],
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)'
                }
            ]
        }
    
    return {'labels': labels, 'datasets': []}


def generate_leave_chart_data(chart_type, period, user):
    """Generate chart data for leave metrics"""
    # Similar implementation for leave data
    return {'labels': [], 'datasets': []}
