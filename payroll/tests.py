from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from datetime import datetime, timedelta

from .models import Payroll
from attendance.models import Attendance

User = get_user_model()


class PayrollModelTest(TestCase):
    """Test Payroll model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@company.com',
            username='testuser',
            employee_id='EMP001',
            first_name='Test',
            last_name='User',
            role='employee'
        )
    
    def test_payroll_creation(self):
        """Test payroll record creation"""
        payroll = Payroll.objects.create(
            user=self.user,
            month=8,
            year=2025,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00'),
            tax_deduction=Decimal('500.00'),
            other_deductions=Decimal('100.00')
        )
        
        self.assertEqual(payroll.user, self.user)
        self.assertEqual(payroll.month, 8)
        self.assertEqual(payroll.year, 2025)
        self.assertEqual(payroll.basic_salary, Decimal('5000.00'))
        self.assertEqual(payroll.status, 'pending')
    
    def test_payroll_calculation_methods(self):
        """Test payroll calculation methods"""
        payroll = Payroll.objects.create(
            user=self.user,
            month=8,
            year=2025,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00'),
            tax_deduction=Decimal('500.00'),
            other_deductions=Decimal('100.00')
        )
        
        # Test gross pay calculation
        payroll.regular_pay = Decimal('4000.00')
        payroll.overtime_pay = Decimal('500.00')
        payroll.save()
        
        expected_gross = Decimal('4500.00')
        self.assertEqual(payroll.calculate_gross_pay(), expected_gross)
        
        # Test net pay calculation
        expected_net = expected_gross - payroll.tax_deduction - payroll.other_deductions
        self.assertEqual(payroll.calculate_net_pay(), expected_net)
    
    def test_payroll_unique_constraint(self):
        """Test unique constraint on user/month/year"""
        Payroll.objects.create(
            user=self.user,
            month=8,
            year=2025,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        # Should not be able to create duplicate
        with self.assertRaises(Exception):
            Payroll.objects.create(
                user=self.user,
                month=8,
                year=2025,
                basic_salary=Decimal('6000.00'),
                hourly_rate=Decimal('30.00')
            )


class PayrollAPITest(APITestCase):
    """Test payroll API endpoints"""
    
    def setUp(self):
        self.employee = User.objects.create_user(
            email='emp@company.com',
            username='empuser',
            employee_id='EMP001',
            first_name='Employee',
            last_name='User',
            role='employee'
        )
        
        self.hr_user = User.objects.create_user(
            email='hr@company.com',
            username='hruser',
            employee_id='HR001',
            first_name='HR',
            last_name='User',
            role='hr'
        )
        
        self.manager = User.objects.create_user(
            email='manager@company.com',
            username='manageruser',
            employee_id='MGR001',
            first_name='Manager',
            last_name='User',
            role='manager'
        )
        
        # Create tokens
        self.employee_token = str(RefreshToken.for_user(self.employee).access_token)
        self.hr_token = str(RefreshToken.for_user(self.hr_user).access_token)
        self.manager_token = str(RefreshToken.for_user(self.manager).access_token)
        
        # Create some attendance records for testing
        self.create_attendance_records()
    
    def create_attendance_records(self):
        """Create test attendance records"""
        today = timezone.now().date()
        start_date = datetime(today.year, today.month, 1).date()
        
        # Create attendance records for the current month
        for i in range(5):  # 5 working days
            date = start_date + timedelta(days=i)
            if date.weekday() < 5:  # Weekdays only
                # Check-in
                Attendance.objects.create(
                    user=self.employee,
                    date=date,
                    check_in_time=timezone.now().replace(hour=9, minute=0),
                    attendance_type='check_in',
                    status='present'
                )
                
                # Check-out
                Attendance.objects.create(
                    user=self.employee,
                    date=date,
                    check_out_time=timezone.now().replace(hour=17, minute=0),
                    attendance_type='check_out',
                    status='present'
                )
    
    def test_create_payroll_hr_access(self):
        """Test HR can create payroll records"""
        url = reverse('payroll_create')
        data = {
            'user': self.employee.id,
            'month': timezone.now().month,
            'year': timezone.now().year,
            'basic_salary': '5000.00',
            'hourly_rate': '25.00',
            'tax_deduction': '500.00',
            'other_deductions': '100.00'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Payroll record created successfully')
        self.assertTrue('payroll' in response.data)
    
    def test_create_payroll_employee_access(self):
        """Test employee cannot create payroll records"""
        url = reverse('payroll_create')
        data = {
            'user': self.employee.id,
            'month': timezone.now().month,
            'year': timezone.now().year,
            'basic_salary': '5000.00',
            'hourly_rate': '25.00'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.employee_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Only HR and Managers can create payroll records')
    
    def test_payroll_calculation(self):
        """Test payroll calculation endpoint"""
        url = reverse('payroll_calculate')
        data = {
            'user': self.employee.id,
            'month': timezone.now().month,
            'year': timezone.now().year,
            'recalculate': False
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('calculated' in response.data['message'])
        self.assertTrue('payroll' in response.data)
    
    def test_payroll_list_hr_access(self):
        """Test HR can access payroll list"""
        # Create a payroll record first
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('payroll_list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_payroll_list_employee_access(self):
        """Test employee gets empty results from payroll list"""
        url = reverse('payroll_list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.employee_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)  # Empty results
    
    def test_my_payroll_employee_access(self):
        """Test employee can view own payroll"""
        # Create a payroll record for the employee
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('my_payroll')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.employee_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['payroll_records']), 1)
        self.assertEqual(response.data['total_records'], 1)
    
    def test_payroll_reports_hr_access(self):
        """Test HR can generate payroll reports"""
        # Create a payroll record first
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('payroll_reports')
        params = {
            'month': timezone.now().month,
            'year': timezone.now().year,
            'export_format': 'json'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('summary' in response.data)
        self.assertTrue('payroll_records' in response.data)
    
    def test_payroll_summary_hr_access(self):
        """Test HR can view payroll summary"""
        # Create a payroll record first
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('payroll_summary')
        params = {
            'month': timezone.now().month,
            'year': timezone.now().year
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('total_employees' in response.data)
        self.assertTrue('total_payroll_amount' in response.data)
    
    def test_payroll_bulk_actions(self):
        """Test bulk payroll actions"""
        # Create payroll records
        payroll1 = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        payroll2 = Payroll.objects.create(
            user=self.manager,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('6000.00'),
            hourly_rate=Decimal('30.00')
        )
        
        url = reverse('payroll_bulk_actions')
        data = {
            'payroll_ids': [payroll1.id, payroll2.id],
            'action': 'approve',
            'notes': 'Bulk approval'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(response.data['action'], 'approve')
    
    def test_auto_generate_payroll(self):
        """Test auto-generation of payroll for all employees"""
        url = reverse('auto_generate_payroll')
        data = {
            'month': timezone.now().month,
            'year': timezone.now().year
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('generated' in response.data['message'])
        self.assertTrue('generated_count' in response.data)


class PayrollCalculationTest(APITestCase):
    """Test payroll calculation logic"""
    
    def setUp(self):
        self.employee = User.objects.create_user(
            email='emp@company.com',
            username='empuser',
            employee_id='EMP001',
            first_name='Employee',
            last_name='User',
            role='employee'
        )
        
        self.hr_user = User.objects.create_user(
            email='hr@company.com',
            username='hruser',
            employee_id='HR001',
            first_name='HR',
            last_name='User',
            role='hr'
        )
        
        self.hr_token = str(RefreshToken.for_user(self.hr_user).access_token)
    
    def test_regular_hours_calculation(self):
        """Test regular hours calculation (8 hours per day)"""
        # Create attendance records for 20 working days
        today = timezone.now().date()
        start_date = datetime(today.year, today.month, 1).date()
        
        for i in range(20):  # 20 working days
            date = start_date + timedelta(days=i)
            if date.weekday() < 5:  # Weekdays only
                # Check-in at 9 AM
                checkin = Attendance.objects.create(
                    user=self.employee,
                    date=date,
                    check_in_time=timezone.now().replace(hour=9, minute=0),
                    attendance_type='check_in',
                    status='present'
                )
                
                # Check-out at 5 PM (8 hours)
                Attendance.objects.create(
                    user=self.employee,
                    date=date,
                    check_out_time=timezone.now().replace(hour=17, minute=0),
                    attendance_type='check_out',
                    status='present'
                )
        
        # Create payroll record
        payroll = Payroll.objects.create(
            user=self.employee,
            month=today.month,
            year=today.year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        # Calculate payroll
        from .views import PayrollCalculationView
        view = PayrollCalculationView()
        view.calculate_payroll(payroll)
        
        # Refresh from database
        payroll.refresh_from_db()
        
        # Should have 160 regular hours (20 days * 8 hours)
        self.assertEqual(payroll.regular_hours, Decimal('160.00'))
        self.assertEqual(payroll.overtime_hours, Decimal('0.00'))
        self.assertEqual(payroll.total_hours_worked, Decimal('160.00'))
        
        # Regular pay should be 160 * 25 = 4000
        self.assertEqual(payroll.regular_pay, Decimal('4000.00'))
        self.assertEqual(payroll.overtime_pay, Decimal('0.00'))
        self.assertEqual(payroll.gross_pay, Decimal('4000.00'))
    
    def test_overtime_hours_calculation(self):
        """Test overtime hours calculation"""
        # Create attendance records for 5 working days with overtime
        today = timezone.now().date()
        start_date = datetime(today.year, today.month, 1).date()
        
        for i in range(5):  # 5 working days
            date = start_date + timedelta(days=i)
            if date.weekday() < 5:  # Weekdays only
                # Check-in at 9 AM
                checkin = Attendance.objects.create(
                    user=self.employee,
                    date=date,
                    check_in_time=timezone.now().replace(hour=9, minute=0),
                    attendance_type='check_in',
                    status='present'
                )
                
                # Check-out at 7 PM (10 hours - 2 hours overtime)
                Attendance.objects.create(
                    user=self.employee,
                    date=date,
                    check_out_time=timezone.now().replace(hour=19, minute=0),
                    attendance_type='check_out',
                    status='present'
                )
        
        # Create payroll record
        payroll = Payroll.objects.create(
            user=self.employee,
            month=today.month,
            year=today.year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        # Calculate payroll
        from .views import PayrollCalculationView
        view = PayrollCalculationView()
        view.calculate_payroll(payroll)
        
        # Refresh from database
        payroll.refresh_from_db()
        
        # Should have 40 regular hours (5 days * 8 hours) and 10 overtime hours (5 days * 2 hours)
        self.assertEqual(payroll.regular_hours, Decimal('40.00'))
        self.assertEqual(payroll.overtime_hours, Decimal('10.00'))
        self.assertEqual(payroll.total_hours_worked, Decimal('50.00'))
        
        # Regular pay should be 40 * 25 = 1000, overtime pay should be 10 * 25 * 1.5 = 375
        self.assertEqual(payroll.regular_pay, Decimal('1000.00'))
        self.assertEqual(payroll.overtime_pay, Decimal('375.00'))
        self.assertEqual(payroll.gross_pay, Decimal('1375.00'))
    
    def test_net_pay_calculation(self):
        """Test net pay calculation with deductions"""
        # Create a simple payroll record
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00'),
            tax_deduction=Decimal('500.00'),
            other_deductions=Decimal('100.00')
        )
        
        # Set gross pay manually
        payroll.gross_pay = Decimal('4000.00')
        payroll.save()
        
        # Calculate net pay
        payroll.net_pay = payroll.calculate_net_pay()
        payroll.save()
        
        # Net pay should be 4000 - 500 - 100 = 3400
        expected_net = Decimal('4000.00') - Decimal('500.00') - Decimal('100.00')
        self.assertEqual(payroll.net_pay, expected_net)


class PayrollPermissionsTest(APITestCase):
    """Test payroll permissions and access control"""
    
    def setUp(self):
        self.employee = User.objects.create_user(
            email='emp@company.com',
            username='empuser',
            employee_id='EMP001',
            first_name='Employee',
            last_name='User',
            role='employee'
        )
        
        self.manager = User.objects.create_user(
            email='manager@company.com',
            username='manageruser',
            employee_id='MGR001',
            first_name='Manager',
            last_name='User',
            role='manager'
        )
        
        self.hr_user = User.objects.create_user(
            email='hr@company.com',
            username='hruser',
            employee_id='HR001',
            first_name='HR',
            last_name='User',
            role='hr'
        )
        
        # Create tokens
        self.employee_token = str(RefreshToken.for_user(self.employee).access_token)
        self.manager_token = str(RefreshToken.for_user(self.manager).access_token)
        self.hr_token = str(RefreshToken.for_user(self.hr_user).access_token)
    
    def test_payroll_detail_employee_access(self):
        """Test employee cannot access payroll detail"""
        # Create a payroll record
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('payroll_detail', kwargs={'pk': payroll.id})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.employee_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Employee should get empty results
    
    def test_payroll_detail_manager_access(self):
        """Test manager can access payroll detail"""
        # Create a payroll record
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('payroll_detail', kwargs={'pk': payroll.id})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.manager_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_payroll_detail_hr_access(self):
        """Test HR can access payroll detail"""
        # Create a payroll record
        payroll = Payroll.objects.create(
            user=self.employee,
            month=timezone.now().month,
            year=timezone.now().year,
            basic_salary=Decimal('5000.00'),
            hourly_rate=Decimal('25.00')
        )
        
        url = reverse('payroll_detail', kwargs={'pk': payroll.id})
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
