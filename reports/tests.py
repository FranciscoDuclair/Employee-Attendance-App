from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, timedelta
from django.utils import timezone

from .models import ReportTemplate, ReportExecution, Dashboard, AnalyticsMetric
from attendance.models import Attendance
from leave.models import LeaveRequest, LeaveType

User = get_user_model()


class ReportTemplateModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='hr'
        )

    def test_create_report_template(self):
        template = ReportTemplate.objects.create(
            name='Test Attendance Report',
            description='Test report for attendance',
            report_type='attendance',
            format_type='pdf',
            fields=['user__name', 'date', 'status'],
            filters={'status': 'present'},
            created_by=self.user
        )
        
        self.assertEqual(template.name, 'Test Attendance Report')
        self.assertEqual(template.report_type, 'attendance')
        self.assertEqual(template.created_by, self.user)
        self.assertTrue(template.is_active)


class ReportExecutionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='hr'
        )
        
        self.template = ReportTemplate.objects.create(
            name='Test Template',
            report_type='attendance',
            format_type='csv',
            created_by=self.user
        )

    def test_create_report_execution(self):
        execution = ReportExecution.objects.create(
            template=self.template,
            name='Test Execution',
            report_type='attendance',
            format_type='csv',
            requested_by=self.user
        )
        
        self.assertEqual(execution.name, 'Test Execution')
        self.assertEqual(execution.status, 'pending')
        self.assertEqual(execution.requested_by, self.user)

    def test_execution_expiry(self):
        # Create execution that expires in the past
        past_time = timezone.now() - timedelta(hours=1)
        execution = ReportExecution.objects.create(
            template=self.template,
            name='Expired Execution',
            report_type='attendance',
            format_type='csv',
            requested_by=self.user,
            expires_at=past_time
        )
        
        self.assertTrue(execution.is_expired)


class ReportAPITest(APITestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            username='hruser',
            email='hr@example.com',
            password='testpass123',
            role='hr'
        )
        
        self.employee_user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='testpass123',
            role='employee'
        )

    def test_create_report_template_as_hr(self):
        """Test HR user can create report templates"""
        self.client.force_authenticate(user=self.hr_user)
        
        data = {
            'name': 'Attendance Report',
            'description': 'Monthly attendance report',
            'report_type': 'attendance',
            'format_type': 'pdf',
            'fields': ['user__name', 'date', 'status'],
            'is_public': True
        }
        
        response = self.client.post(reverse('report-template-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReportTemplate.objects.count(), 1)

    def test_create_report_template_as_employee(self):
        """Test employee user has limited access"""
        self.client.force_authenticate(user=self.employee_user)
        
        data = {
            'name': 'Personal Report',
            'report_type': 'attendance',
            'format_type': 'csv',
            'is_public': False
        }
        
        response = self.client.post(reverse('report-template-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        template = ReportTemplate.objects.first()
        self.assertEqual(template.created_by, self.employee_user)
        self.assertFalse(template.is_public)  # Forced to private for employees

    def test_generate_attendance_report(self):
        """Test quick attendance report generation"""
        self.client.force_authenticate(user=self.hr_user)
        
        # Create some test attendance data
        Attendance.objects.create(
            user=self.employee_user,
            date=timezone.now().date(),
            status='present',
            hours_worked=8.0
        )
        
        data = {
            'start_date': (timezone.now().date() - timedelta(days=7)).isoformat(),
            'end_date': timezone.now().date().isoformat(),
            'format': 'json'
        }
        
        response = self.client.post(reverse('generate-attendance-report'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('count', response.data)

    def test_analytics_data(self):
        """Test analytics endpoint"""
        self.client.force_authenticate(user=self.hr_user)
        
        response = self.client.get(reverse('analytics-data'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('attendance_metrics', response.data)
        self.assertIn('leave_metrics', response.data)


class DashboardModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='manager'
        )

    def test_create_dashboard(self):
        dashboard = Dashboard.objects.create(
            name='HR Dashboard',
            description='Dashboard for HR team',
            dashboard_type='hr',
            widgets=[
                {
                    'type': 'attendance_summary',
                    'title': 'Attendance Overview',
                    'params': {}
                }
            ],
            layout={'columns': 3, 'rows': 2},
            created_by=self.user
        )
        
        self.assertEqual(dashboard.name, 'HR Dashboard')
        self.assertEqual(dashboard.dashboard_type, 'hr')
        self.assertEqual(len(dashboard.widgets), 1)
        self.assertEqual(dashboard.created_by, self.user)


class AnalyticsMetricModelTest(TestCase):
    def test_create_analytics_metric(self):
        metric = AnalyticsMetric.objects.create(
            name='Attendance Rate',
            metric_type='attendance_rate',
            description='Overall attendance rate percentage',
            current_value=95.5,
            previous_value=93.2,
            target_value=98.0,
            unit='%'
        )
        
        self.assertEqual(metric.name, 'Attendance Rate')
        self.assertEqual(metric.trend, 'up')  # Current > Previous
        self.assertAlmostEqual(float(metric.target_achievement), 97.45, places=2)

    def test_metric_trend_calculation(self):
        # Test upward trend
        metric_up = AnalyticsMetric.objects.create(
            name='Test Up',
            metric_type='custom',
            current_value=100,
            previous_value=90
        )
        self.assertEqual(metric_up.trend, 'up')
        
        # Test downward trend
        metric_down = AnalyticsMetric.objects.create(
            name='Test Down',
            metric_type='custom',
            current_value=80,
            previous_value=90
        )
        self.assertEqual(metric_down.trend, 'down')
        
        # Test stable trend
        metric_stable = AnalyticsMetric.objects.create(
            name='Test Stable',
            metric_type='custom',
            current_value=90,
            previous_value=90
        )
        self.assertEqual(metric_stable.trend, 'stable')


class ReportUtilsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='employee'
        )

    def test_calculate_attendance_metrics(self):
        """Test attendance metrics calculation"""
        from .utils import calculate_attendance_metrics
        
        # Create test attendance data
        today = timezone.now().date()
        Attendance.objects.create(
            user=self.user,
            date=today,
            status='present',
            hours_worked=8.0
        )
        Attendance.objects.create(
            user=self.user,
            date=today - timedelta(days=1),
            status='late',
            hours_worked=7.5
        )
        
        metrics = calculate_attendance_metrics(
            today - timedelta(days=7),
            today
        )
        
        self.assertIn('total_records', metrics)
        self.assertIn('attendance_rate', metrics)
        self.assertIn('status_distribution', metrics)
        self.assertEqual(metrics['total_records'], 2)

    def test_create_dashboard_widgets(self):
        """Test dashboard widget creation"""
        from .utils import create_dashboard_widgets
        
        widget_config = {
            'type': 'attendance_summary',
            'title': 'My Attendance',
            'params': {}
        }
        
        widget_data = create_dashboard_widgets(widget_config, self.user)
        
        self.assertEqual(widget_data['type'], 'attendance_summary')
        self.assertEqual(widget_data['title'], 'My Attendance')
        self.assertIn('data', widget_data)


class ReportGenerationIntegrationTest(APITestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            username='hruser',
            email='hr@example.com',
            password='testpass123',
            role='hr'
        )
        
        self.employee_user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='testpass123',
            role='employee'
        )
        
        # Create test data
        today = timezone.now().date()
        Attendance.objects.create(
            user=self.employee_user,
            date=today,
            status='present',
            hours_worked=8.0
        )
        
        # Create leave type and request
        leave_type = LeaveType.objects.create(
            name='Annual Leave',
            max_days_per_year=20
        )
        LeaveRequest.objects.create(
            user=self.employee_user,
            leave_type=leave_type,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=2),
            total_days=2,
            reason='Personal'
        )

    def test_full_report_workflow(self):
        """Test complete report generation workflow"""
        self.client.force_authenticate(user=self.hr_user)
        
        # 1. Create report template
        template_data = {
            'name': 'Weekly Attendance Report',
            'report_type': 'attendance',
            'format_type': 'json',
            'fields': ['user__name', 'date', 'status'],
            'filters': {}
        }
        
        template_response = self.client.post(
            reverse('report-template-list'),
            template_data,
            format='json'
        )
        self.assertEqual(template_response.status_code, status.HTTP_201_CREATED)
        template_id = template_response.data['id']
        
        # 2. Create report execution
        execution_data = {
            'template': template_id,
            'name': 'Weekly Report - ' + timezone.now().strftime('%Y-%m-%d'),
            'report_type': 'attendance',
            'format_type': 'json',
            'filters': {
                'start_date': (timezone.now().date() - timedelta(days=7)).isoformat(),
                'end_date': timezone.now().date().isoformat()
            }
        }
        
        execution_response = self.client.post(
            reverse('report-execution-list'),
            execution_data,
            format='json'
        )
        self.assertEqual(execution_response.status_code, status.HTTP_201_CREATED)
        
        # 3. Check execution status
        execution_id = execution_response.data['id']
        detail_response = self.client.get(
            reverse('report-execution-detail', kwargs={'pk': execution_id})
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        
        # Note: In a real scenario, the report would be processed asynchronously
        # and we'd need to wait for completion before downloading
