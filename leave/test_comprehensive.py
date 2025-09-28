# Comprehensive Leave Management Tests
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta
from users.models import User
from .models import LeaveType, LeaveRequest, LeaveBalance


class LeaveTestCase(APITestCase):
    """Comprehensive test case for leave management"""
    
    def setUp(self):
        # Create test users
        self.employee = User.objects.create_user(
            email='emp@test.com', username='emp', employee_id='EMP001',
            first_name='John', last_name='Doe', role='employee', password='test123'
        )
        
        self.hr_user = User.objects.create_user(
            email='hr@test.com', username='hr', employee_id='HR001',
            first_name='Jane', last_name='Smith', role='hr', password='test123'
        )
        
        # Create leave types
        self.annual_leave = LeaveType.objects.create(
            name='Annual Leave', max_days_per_year=21, requires_approval=True,
            is_paid=True, is_active=True
        )
        
        self.sick_leave = LeaveType.objects.create(
            name='Sick Leave', max_days_per_year=12, requires_approval=False,
            is_paid=True, is_active=True
        )
        
        # Create leave balance
        LeaveBalance.objects.create(
            user=self.employee, leave_type=self.annual_leave,
            year=date.today().year, total_allocated=21, used_days=0
        )
    
    def test_leave_request_creation(self):
        """Test creating leave request with proper validation"""
        self.client.force_authenticate(user=self.employee)
        
        start_date = date.today() + timedelta(days=30)
        end_date = start_date + timedelta(days=4)  # 5 working days
        
        data = {
            'leave_type': self.annual_leave.id,
            'start_date': start_date,
            'end_date': end_date,
            'reason': 'Family vacation'
        }
        
        response = self.client.post('/api/leave/requests/create/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        leave_request = LeaveRequest.objects.get(id=response.data['id'])
        self.assertEqual(leave_request.total_days, 5)
        self.assertEqual(leave_request.status, 'pending')
    
    def test_leave_approval_workflow(self):
        """Test leave approval by HR"""
        # Create leave request
        leave_request = LeaveRequest.objects.create(
            user=self.employee, leave_type=self.annual_leave,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            total_days=3, reason='Test', status='pending'
        )
        
        self.client.force_authenticate(user=self.hr_user)
        
        data = {'status': 'approved', 'approval_notes': 'Approved'}
        response = self.client.post(f'/api/leave/requests/{leave_request.id}/approve/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check leave balance was updated
        balance = LeaveBalance.objects.get(user=self.employee, leave_type=self.annual_leave)
        self.assertEqual(balance.used_days, 3)
        self.assertEqual(balance.remaining_days, 18)
    
    def test_insufficient_balance_validation(self):
        """Test validation when requesting more leave than available"""
        self.client.force_authenticate(user=self.employee)
        
        # Request 30 days when only 21 are allocated
        start_date = date.today() + timedelta(days=30)
        end_date = start_date + timedelta(days=29)  # 30 days
        
        data = {
            'leave_type': self.annual_leave.id,
            'start_date': start_date,
            'end_date': end_date,
            'reason': 'Too much leave'
        }
        
        response = self.client.post('/api/leave/requests/create/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient leave balance', str(response.data))
    
    def test_weekend_exclusion_calculation(self):
        """Test that weekends are excluded from leave calculation"""
        # Friday to Monday (should count only 2 working days)
        start_date = date(2025, 3, 7)   # Friday
        end_date = date(2025, 3, 10)    # Monday
        
        leave_request = LeaveRequest(
            user=self.employee, leave_type=self.annual_leave,
            start_date=start_date, end_date=end_date, reason='Test'
        )
        
        calculated_days = leave_request.calculate_total_days()
        self.assertEqual(calculated_days, 2)  # Friday and Monday only
    
    def test_bulk_leave_operations(self):
        """Test bulk approval of leave requests"""
        # Create multiple leave requests
        leave1 = LeaveRequest.objects.create(
            user=self.employee, leave_type=self.annual_leave,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=31),
            total_days=2, reason='Leave 1', status='pending'
        )
        
        leave2 = LeaveRequest.objects.create(
            user=self.employee, leave_type=self.sick_leave,
            start_date=date.today() + timedelta(days=40),
            end_date=date.today() + timedelta(days=41),
            total_days=2, reason='Leave 2', status='pending'
        )
        
        self.client.force_authenticate(user=self.hr_user)
        
        data = {
            'leave_ids': [leave1.id, leave2.id],
            'action': 'approve',
            'approval_notes': 'Bulk approved'
        }
        
        response = self.client.post('/api/leave/requests/bulk-actions/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
    
    def test_leave_calendar_view(self):
        """Test leave calendar functionality"""
        # Create approved leave
        LeaveRequest.objects.create(
            user=self.employee, leave_type=self.annual_leave,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            total_days=3, reason='Calendar test', status='approved'
        )
        
        self.client.force_authenticate(user=self.employee)
        response = self.client.get('/api/leave/calendar/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['calendar_events']), 1)
    
    def test_leave_statistics(self):
        """Test leave statistics endpoint"""
        # Create test data
        LeaveRequest.objects.create(
            user=self.employee, leave_type=self.annual_leave,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            total_days=3, reason='Stats test', status='approved'
        )
        
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get('/api/leave/statistics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertGreater(response.data['summary']['total_leave_requests'], 0)
