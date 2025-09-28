from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Sum, Avg, Count, F
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters
from datetime import datetime, timedelta
import csv
from io import StringIO
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from utils.currency import format_currency

from .models import Payroll
from .serializers import (
    PayrollSerializer, PayrollCreateSerializer, PayrollUpdateSerializer,
    PayrollCalculationSerializer, PayrollReportSerializer, PayrollSummarySerializer,
    PayrollBulkActionSerializer, PayrollExportSerializer, PayrollAdjustmentSerializer,
    PayrollComparisonSerializer, PayrollTaxCalculationSerializer
)
from users.models import User
from attendance.models import Attendance
# Import notification utilities
try:
    from notifications.utils import send_payroll_notification
except ImportError:
    # Fallback if notifications app is not available
    def send_payroll_notification(*args, **kwargs):
        pass


class PayrollListView(generics.ListAPIView):
    """List all payroll records (HR/Admin only)"""
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'month', 'year', 'status', 'department'] if DjangoFilterBackend else []
    search_fields = ['user__first_name', 'user__last_name', 'user__employee_id']
    ordering_fields = ['month', 'year', 'gross_pay', 'net_pay', 'created_at']
    ordering = ['-year', '-month', '-created_at']
    
    def get_queryset(self):
        if not self.request.user.can_manage_attendance():
            return Payroll.objects.none()
        
        queryset = Payroll.objects.select_related('user', 'approved_by')
        
        # Filter by department if specified
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(user__department=department)
        
        return queryset


class PayrollDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Payroll record detail view (HR/Admin only)"""
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if not self.request.user.can_manage_attendance():
            return Payroll.objects.none()
        return Payroll.objects.select_related('user', 'approved_by')


class PayrollCreateView(APIView):
    """Create new payroll record (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can create payroll records'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PayrollCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            payroll = serializer.save()
            
            # Auto-calculate payroll based on attendance
            self.calculate_payroll(payroll)
            
            # Send notification
            send_payroll_notification(payroll, 'generated')
            
            return Response({
                'message': 'Payroll record created successfully',
                'payroll': PayrollSerializer(payroll).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def calculate_payroll(self, payroll):
        """Calculate payroll based on attendance records"""
        user = payroll.user
        month = payroll.month
        year = payroll.year
        
        # Get attendance records for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Get all attendance records for the month
        attendance_records = Attendance.objects.filter(
            user=user,
            date__range=[start_date, end_date],
            status__in=['present', 'late']
        )
        
        # Calculate total hours worked
        total_hours = Decimal('0.00')
        for record in attendance_records:
            if record.hours_worked > 0:
                total_hours += Decimal(str(record.hours_worked))
        
        # Calculate regular and overtime hours
        regular_hours = min(total_hours, Decimal('160.00'))  # 160 hours = 8 hours * 20 working days
        overtime_hours = max(total_hours - Decimal('160.00'), Decimal('0.00'))
        
        # Calculate pay
        regular_pay = regular_hours * payroll.hourly_rate
        overtime_pay = overtime_hours * (payroll.hourly_rate * Decimal('1.5'))
        
        # Calculate gross pay
        gross_pay = regular_pay + overtime_pay
        
        # Calculate net pay
        net_pay = gross_pay - payroll.tax_deduction - payroll.other_deductions
        
        # Update payroll record
        payroll.total_hours_worked = total_hours
        payroll.regular_hours = regular_hours
        payroll.overtime_hours = overtime_hours
        payroll.regular_pay = regular_pay
        payroll.overtime_pay = overtime_pay
        payroll.gross_pay = gross_pay
        payroll.net_pay = net_pay
        payroll.save()


class PayrollCalculationView(APIView):
    """Calculate or recalculate payroll (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can calculate payroll'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PayrollCalculationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            month = serializer.validated_data['month']
            year = serializer.validated_data['year']
            recalculate = serializer.validated_data.get('recalculate', False)
            
            # Get or create payroll record
            payroll, created = Payroll.objects.get_or_create(
                user=user,
                month=month,
                year=year,
                defaults={
                    'basic_salary': user.basic_salary if hasattr(user, 'basic_salary') else Decimal('0.00'),
                    'hourly_rate': user.hourly_rate if hasattr(user, 'hourly_rate') else Decimal('0.00'),
                    'tax_deduction': Decimal('0.00'),
                    'other_deductions': Decimal('0.00'),
                    'status': 'pending'
                }
            )
            
            # Calculate payroll
            self.calculate_payroll(payroll)
            
            action = 'recalculated' if not created else 'calculated'
            return Response({
                'message': f'Payroll {action} successfully for {user.get_full_name()} - {month}/{year}',
                'payroll': PayrollSerializer(payroll).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def calculate_payroll(self, payroll):
        """Calculate payroll based on attendance records"""
        user = payroll.user
        month = payroll.month
        year = payroll.year
        
        # Get attendance records for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Get all attendance records for the month
        attendance_records = Attendance.objects.filter(
            user=user,
            date__range=[start_date, end_date],
            status__in=['present', 'late']
        )
        
        # Calculate total hours worked
        total_hours = Decimal('0.00')
        for record in attendance_records:
            if record.hours_worked > 0:
                total_hours += Decimal(str(record.hours_worked))
        
        # Calculate regular and overtime hours
        regular_hours = min(total_hours, Decimal('160.00'))  # 160 hours = 8 hours * 20 working days
        overtime_hours = max(total_hours - Decimal('160.00'), Decimal('0.00'))
        
        # Calculate pay
        regular_pay = regular_hours * payroll.hourly_rate
        overtime_pay = overtime_hours * (payroll.hourly_rate * Decimal('1.5'))
        
        # Calculate gross pay
        gross_pay = regular_pay + overtime_pay
        
        # Calculate net pay
        net_pay = gross_pay - payroll.tax_deduction - payroll.other_deductions
        
        # Update payroll record
        payroll.total_hours_worked = total_hours
        payroll.regular_hours = regular_hours
        payroll.overtime_hours = overtime_hours
        payroll.regular_pay = regular_pay
        payroll.overtime_pay = overtime_pay
        payroll.gross_pay = gross_pay
        payroll.net_pay = net_pay
        payroll.save()


class PayrollReportView(APIView):
    """Generate payroll reports (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can generate payroll reports'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PayrollReportSerializer(data=request.query_params)
        if serializer.is_valid():
            month = serializer.validated_data.get('month')
            year = serializer.validated_data.get('year')
            department = serializer.validated_data.get('department')
            status_filter = serializer.validated_data.get('status')
            export_format = serializer.validated_data.get('export_format', 'json')
            
            # Build queryset
            queryset = Payroll.objects.select_related('user')
            
            if month:
                queryset = queryset.filter(month=month)
            if year:
                queryset = queryset.filter(year=year)
            if department:
                queryset = queryset.filter(user__department=department)
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Get summary data
            summary = self.get_payroll_summary(queryset)
            
            if export_format == 'csv':
                return self.export_to_csv(queryset, summary)
            elif export_format == 'pdf':
                return self.export_to_pdf(queryset, summary)
            else:
                # Return JSON response
                payroll_data = PayrollSerializer(queryset, many=True).data
                return Response({
                    'summary': summary,
                    'payroll_records': payroll_data,
                    'total_records': len(payroll_data)
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_payroll_summary(self, queryset):
        """Calculate payroll summary statistics"""
        total_employees = queryset.count()
        total_payroll = queryset.aggregate(
            total=Sum('net_pay'),
            gross=Sum('gross_pay'),
            overtime=Sum('overtime_pay'),
            tax=Sum('tax_deduction'),
            other=Sum('other_deductions')
        )
        
        return {
            'total_employees': total_employees,
            'total_payroll_amount': total_payroll['total'] or Decimal('0.00'),
            'total_gross_pay': total_payroll['gross'] or Decimal('0.00'),
            'average_salary': (total_payroll['total'] / total_employees) if total_employees > 0 else Decimal('0.00'),
            'total_overtime_pay': total_payroll['overtime'] or Decimal('0.00'),
            'total_tax_deductions': total_payroll['tax'] or Decimal('0.00'),
            'total_other_deductions': total_payroll['other'] or Decimal('0.00')
        }
    
    def export_to_csv(self, queryset, summary):
        """Export payroll data to CSV"""
        response = Response(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payroll_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'Name', 'Department', 'Month', 'Year',
            'Basic Salary', 'Hourly Rate', 'Total Hours', 'Regular Hours',
            'Overtime Hours', 'Regular Pay', 'Overtime Pay', 'Gross Pay',
            'Tax Deduction', 'Other Deductions', 'Net Pay', 'Status'
        ])
        
        for payroll in queryset:
            writer.writerow([
                payroll.user.employee_id,
                payroll.user.get_full_name(),
                payroll.user.department,
                payroll.month,
                payroll.year,
                payroll.basic_salary,
                payroll.hourly_rate,
                payroll.total_hours_worked,
                payroll.regular_hours,
                payroll.overtime_hours,
                payroll.regular_pay,
                payroll.overtime_pay,
                payroll.gross_pay,
                payroll.tax_deduction,
                payroll.other_deductions,
                payroll.net_pay,
                payroll.status
            ])
        
        return response
    
    def export_to_pdf(self, queryset, summary):
        """Export payroll data to PDF (placeholder)"""
        # This would integrate with a PDF library like ReportLab
        return Response({
            'message': 'PDF export not yet implemented. Use CSV export instead.',
            'summary': summary
        })


class PayrollSummaryView(APIView):
    """Get payroll summary statistics (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can view payroll summaries'
            }, status=status.HTTP_403_FORBIDDEN)
        
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        department = request.query_params.get('department')
        
        # Build queryset
        queryset = Payroll.objects.select_related('user')
        
        if month:
            queryset = queryset.filter(month=month)
        if year:
            queryset = queryset.filter(year=year)
        if department:
            queryset = queryset.filter(user__department=department)
        
        # Calculate summary
        summary = self.calculate_summary(queryset)
        
        return Response(summary)
    
    def calculate_summary(self, queryset):
        """Calculate comprehensive payroll summary"""
        total_employees = queryset.count()
        
        if total_employees == 0:
            return {
                'total_employees': 0,
                'total_payroll_amount': Decimal('0.00'),
                'average_salary': Decimal('0.00'),
                'total_overtime_hours': Decimal('0.00'),
                'total_overtime_pay': Decimal('0.00'),
                'total_tax_deductions': Decimal('0.00'),
                'total_other_deductions': Decimal('0.00'),
                'department_breakdown': {},
                'status_breakdown': {}
            }
        
        # Basic calculations
        totals = queryset.aggregate(
            total_payroll=Sum('net_pay'),
            total_gross=Sum('gross_pay'),
            total_overtime_hours=Sum('overtime_hours'),
            total_overtime_pay=Sum('overtime_pay'),
            total_tax=Sum('tax_deduction'),
            total_other=Sum('other_deductions')
        )
        
        # Department breakdown
        dept_breakdown = queryset.values('user__department').annotate(
            count=Count('id'),
            total=Sum('net_pay'),
            avg=Avg('net_pay')
        ).order_by('-total')
        
        # Status breakdown
        status_breakdown = queryset.values('status').annotate(
            count=Count('id'),
            total=Sum('net_pay')
        ).order_by('-total')
        
        return {
            'total_employees': total_employees,
            'total_payroll_amount': totals['total_payroll'] or Decimal('0.00'),
            'average_salary': (totals['total_payroll'] / total_employees) if totals['total_payroll'] else Decimal('0.00'),
            'total_overtime_hours': totals['total_overtime_hours'] or Decimal('0.00'),
            'total_overtime_pay': totals['total_overtime_pay'] or Decimal('0.00'),
            'total_tax_deductions': totals['total_tax'] or Decimal('0.00'),
            'total_other_deductions': totals['total_other'] or Decimal('0.00'),
            'department_breakdown': list(dept_breakdown),
            'status_breakdown': list(status_breakdown)
        }


class PayrollBulkActionView(APIView):
    """Perform bulk actions on payroll records (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can perform bulk payroll actions'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PayrollBulkActionSerializer(data=request.data)
        if serializer.is_valid():
            payroll_ids = serializer.validated_data['payroll_ids']
            action = serializer.validated_data['action']
            notes = serializer.validated_data.get('notes', '')
            
            payroll_records = Payroll.objects.filter(id__in=payroll_ids)
            updated_count = 0
            
            if action == 'approve':
                for payroll in payroll_records:
                    payroll.status = 'approved'
                    payroll.approved_by = request.user
                    payroll.approved_at = timezone.now()
                    payroll.save()
                    updated_count += 1
                
                message = f'{updated_count} payroll records approved successfully'
                
            elif action == 'reject':
                for payroll in payroll_records:
                    payroll.status = 'rejected'
                    payroll.save()
                    updated_count += 1
                
                message = f'{updated_count} payroll records rejected successfully'
                
            elif action == 'delete':
                for payroll in payroll_records:
                    payroll.delete()
                    updated_count += 1
                
                message = f'{updated_count} payroll records deleted successfully'
            
            return Response({
                'message': message,
                'updated_count': updated_count,
                'action': action
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PayrollAdjustmentView(APIView):
    """Make adjustments to payroll records (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can make payroll adjustments'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PayrollAdjustmentSerializer(data=request.data)
        if serializer.is_valid():
            payroll_id = serializer.validated_data['payroll_id']
            adjustment_type = serializer.validated_data['adjustment_type']
            amount = serializer.validated_data['amount']
            reason = serializer.validated_data['reason']
            approved_by = serializer.validated_data['approved_by']
            
            try:
                payroll = Payroll.objects.get(id=payroll_id)
            except Payroll.DoesNotExist:
                return Response({
                    'error': 'Payroll record not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Apply adjustment
            if adjustment_type == 'bonus':
                payroll.other_deductions -= amount  # Reduce deductions (add bonus)
            elif adjustment_type == 'deduction':
                payroll.other_deductions += amount  # Add deduction
            elif adjustment_type == 'correction':
                # For corrections, we need to know what to correct
                # This is a simplified version
                payroll.other_deductions += amount
            
            # Recalculate net pay
            payroll.net_pay = payroll.gross_pay - payroll.tax_deduction - payroll.other_deductions
            payroll.save()
            
            return Response({
                'message': f'{adjustment_type.title()} adjustment applied successfully',
                'payroll': PayrollSerializer(payroll).data,
                'adjustment_amount': amount,
                'reason': reason
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PayrollComparisonView(APIView):
    """Compare payroll between two periods (HR/Admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if not request.user.can_manage_attendance():
            return Response({
                'error': 'Only HR and Managers can compare payroll periods'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PayrollComparisonSerializer(data=request.data)
        if serializer.is_valid():
            period1_month = serializer.validated_data['period1_month']
            period1_year = serializer.validated_data['period1_year']
            period2_month = serializer.validated_data['period2_month']
            period2_year = serializer.validated_data['period2_year']
            user = serializer.validated_data.get('user')
            
            # Build querysets for both periods
            period1_qs = Payroll.objects.filter(month=period1_month, year=period1_year)
            period2_qs = Payroll.objects.filter(month=period2_month, year=period2_year)
            
            if user:
                period1_qs = period1_qs.filter(user=user)
                period2_qs = period2_qs.filter(user=user)
            
            # Calculate summaries for both periods
            period1_summary = self.calculate_period_summary(period1_qs)
            period2_summary = self.calculate_period_summary(period2_qs)
            
            # Calculate differences
            differences = self.calculate_differences(period1_summary, period2_summary)
            
            return Response({
                'period1': {
                    'month': period1_month,
                    'year': period1_year,
                    'summary': period1_summary
                },
                'period2': {
                    'month': period2_month,
                    'year': period2_year,
                    'summary': period2_summary
                },
                'differences': differences
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def calculate_period_summary(self, queryset):
        """Calculate summary for a specific period"""
        return queryset.aggregate(
            total_employees=Count('id'),
            total_payroll=Sum('net_pay'),
            total_gross=Sum('gross_pay'),
            total_overtime=Sum('overtime_pay'),
            total_tax=Sum('tax_deduction'),
            total_other=Sum('other_deductions'),
            avg_salary=Avg('net_pay')
        )
    
    def calculate_differences(self, period1, period2):
        """Calculate differences between two periods"""
        differences = {}
        for key in period1.keys():
            if key == 'total_employees':
                differences[key] = (period2[key] or 0) - (period1[key] or 0)
            else:
                val1 = period1[key] or Decimal('0.00')
                val2 = period2[key] or Decimal('0.00')
                differences[key] = val2 - val1
                
                # Calculate percentage change
                if val1 != 0:
                    pct_change = ((val2 - val1) / val1) * 100
                    differences[f'{key}_pct_change'] = pct_change
        
        return differences


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_payroll(request):
    """Get current user's payroll records"""
    user = request.user
    month = request.query_params.get('month')
    year = request.query_params.get('year')
    
    queryset = Payroll.objects.filter(user=user)
    
    if month:
        queryset = queryset.filter(month=month)
    if year:
        queryset = queryset.filter(year=year)
    
    payroll_data = PayrollSerializer(queryset, many=True).data
    
    return Response({
        'payroll_records': payroll_data,
        'total_records': len(payroll_data)
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def auto_generate_payroll(request):
    """Auto-generate payroll for all employees for a specific month (HR/Admin only)"""
    if not request.user.can_manage_attendance():
        return Response({
            'error': 'Only HR and Managers can auto-generate payroll'
        }, status=status.HTTP_403_FORBIDDEN)
    
    month = request.data.get('month')
    year = request.data.get('year')
    
    if not month or not year:
        return Response({
            'error': 'Month and year are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get all active employees
    employees = User.objects.filter(is_active=True, role='employee')
    
    generated_count = 0
    errors = []
    
    for employee in employees:
        try:
            # Check if payroll already exists
            if Payroll.objects.filter(user=employee, month=month, year=year).exists():
                continue
            
            # Create payroll record
            payroll = Payroll.objects.create(
                user=employee,
                month=month,
                year=year,
                basic_salary=getattr(employee, 'basic_salary', Decimal('0.00')),
                hourly_rate=getattr(employee, 'hourly_rate', Decimal('0.00')),
                tax_deduction=Decimal('0.00'),
                other_deductions=Decimal('0.00'),
                status='pending'
            )
            
            # Calculate payroll
            view = PayrollCalculationView()
            view.calculate_payroll(payroll)
            
            generated_count += 1
            
        except Exception as e:
            errors.append(f"Error generating payroll for {employee.get_full_name()}: {str(e)}")
    
    return Response({
        'message': f'Payroll generation completed. {generated_count} records generated.',
        'generated_count': generated_count,
        'errors': errors
    }, status=status.HTTP_200_OK)


@login_required
def generate_payslips_web(request):
    """Web-based payslip generation view for HR/Admin"""
    user = request.user
    
    # Check if user can generate payslips
    if not user.can_manage_attendance():
        return render(request, 'payroll/access_denied.html')
    
    if request.method == 'POST':
        month = request.POST.get('month')
        year = request.POST.get('year')
        
        if not month or not year:
            messages.error(request, 'Month and year are required.')
            return render(request, 'payroll/generate_payslips.html')
        
        try:
            # Get all active employees
            employees = User.objects.filter(is_active=True, role='employee')
            
            generated_count = 0
            errors = []
            
            for employee in employees:
                try:
                    # Check if payroll already exists
                    if Payroll.objects.filter(user=employee, month=month, year=year).exists():
                        continue
                    
                    # Create payroll record
                    payroll = Payroll.objects.create(
                        user=employee,
                        month=month,
                        year=year,
                        basic_salary=getattr(employee, 'basic_salary', Decimal('0.00')),
                        hourly_rate=getattr(employee, 'hourly_rate', Decimal('0.00')),
                        tax_deduction=Decimal('0.00'),
                        other_deductions=Decimal('0.00'),
                        status='pending'
                    )
                    
                    # Calculate payroll
                    view = PayrollCalculationView()
                    view.calculate_payroll(payroll)
                    
                    generated_count += 1
                    
                except Exception as e:
                    errors.append(f"Error generating payroll for {employee.get_full_name()}: {str(e)}")
            
            if errors:
                messages.warning(request, f'Payroll generation completed with {len(errors)} errors. {generated_count} records generated.')
                for error in errors[:5]:  # Show first 5 errors
                    messages.error(request, error)
            else:
                messages.success(request, f'Payroll generation completed successfully. {generated_count} records generated.')
                
        except Exception as e:
            messages.error(request, f'Error during payroll generation: {str(e)}')
    
    context = {
        'current_month': timezone.now().month,
        'current_year': timezone.now().year,
    }
    
    return render(request, 'payroll/generate_payslips.html', context)


@login_required
def payroll_web_view(request):
    """Web-based payroll view for employees"""
    user = request.user
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    queryset = Payroll.objects.filter(user=user)
    
    if month:
        queryset = queryset.filter(month=month)
    if year:
        queryset = queryset.filter(year=year)
    
    # Get recent payroll records
    payroll_records = queryset.order_by('-year', '-month')
    
    # Get current month payroll if exists
    current_month = timezone.now().month
    current_year = timezone.now().year
    current_payroll = queryset.filter(month=current_month, year=current_year).first()
    
    context = {
        'payroll_records': payroll_records,
        'current_payroll': current_payroll,
        'month_filter': month,
        'year_filter': year,
        'current_month': current_month,
        'current_year': current_year,
    }
    
    return render(request, 'payroll/my_payroll.html', context)


@login_required
def payslip_download_web(request):
    """Web-based payslip download"""
    user = request.user
    payroll_id = request.GET.get('payroll_id')
    
    if payroll_id:
        try:
            payroll = Payroll.objects.get(id=payroll_id, user=user)
        except Payroll.DoesNotExist:
            return HttpResponse("Payroll record not found", status=404)
    else:
        # Get latest payroll record
        payroll = Payroll.objects.filter(user=user).order_by('-year', '-month').first()
        if not payroll:
            return HttpResponse("No payroll records found", status=404)
    
    # Generate CSV payslip
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="payslip_{payroll.user.employee_id}_{payroll.month}_{payroll.year}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['PAYSLIP'])
    writer.writerow(['Employee ID', payroll.user.employee_id])
    writer.writerow(['Name', payroll.user.get_full_name()])
    writer.writerow(['Department', getattr(payroll.user, 'department', 'N/A')])
    writer.writerow(['Month/Year', f"{payroll.month}/{payroll.year}"])
    writer.writerow([])
    writer.writerow(['EARNINGS'])
    writer.writerow(['Basic Salary', f"${payroll.basic_salary}"])
    writer.writerow(['Regular Pay', f"${payroll.regular_pay}"])
    writer.writerow(['Overtime Pay', f"${payroll.overtime_pay}"])
    writer.writerow(['Gross Pay', f"${payroll.gross_pay}"])
    writer.writerow([])
    writer.writerow(['DEDUCTIONS'])
    writer.writerow(['Tax Deduction', f"${payroll.tax_deduction}"])
    writer.writerow(['Other Deductions', f"${payroll.other_deductions}"])
    writer.writerow([])
    writer.writerow(['NET PAY', f"${payroll.net_pay}"])
    writer.writerow([])
    writer.writerow(['HOURS'])
    writer.writerow(['Total Hours Worked', f"{payroll.total_hours_worked}"])
    writer.writerow(['Regular Hours', f"{payroll.regular_hours}"])
    writer.writerow(['Overtime Hours', f"{payroll.overtime_hours}"])
    
    return response
