# Comprehensive Shift Management Tests
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, timedelta, time
from users.models import User
from .models import Shift, ShiftTemplate, ShiftSchedule


class ShiftTestCase(APITestCase):
    """Comprehensive test case for shift management"""
    
    def setUp(self):
        # Create test users
        self.employee = User.objects.create_user(
            email='emp@test.com', username='emp', employee_id='EMP001',
            first_name='John', last_name='Doe', role='employee', password='test123'
        )
        
        self.manager = User.objects.create_user(
            email='mgr@test.com', username='mgr', employee_id='MGR001',
            first_name='Jane', last_name='Smith', role='manager', password='test123'
        )
        
        self.hr_user = User.objects.create_user(
            email='hr@test.com', username='hr', employee_id='HR001',
            first_name='Bob', last_name='Johnson', role='hr', password='test123'
        )
        
        # Create shifts
        self.morning_shift = Shift.objects.create(
            name='Morning Shift',
            start_time=time(9, 0),
            end_time=time(17, 0),
            break_duration=60,
            is_active=True
        )
        
        self.night_shift = Shift.objects.create(
            name='Night Shift',
            start_time=time(21, 0),
            end_time=time(5, 0),
            break_duration=60,
            is_active=True
        )
        
        # Create shift template
        self.template = ShiftTemplate.objects.create(
            name='Weekly Morning Template',
            shift=self.morning_shift,
            frequency='weekly',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            created_by=self.manager
        )
    
    def test_shift_creation(self):
        """Test creating a shift (Manager/HR only)"""
        self.client.force_authenticate(user=self.employee)
        
        data = {
            'name': 'Evening Shift',
            'start_time': '14:00:00',
            'end_time': '22:00:00',
            'break_duration': 60,
            'is_active': True
        }
        
        response = self.client.post('/api/shifts/shifts/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Manager should be able to create
        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/shifts/shifts/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Shift.objects.filter(name='Evening Shift').count(), 1)
    
    def test_shift_schedule_creation(self):
        """Test creating shift schedules"""
        self.client.force_authenticate(user=self.manager)
        
        tomorrow = date.today() + timedelta(days=1)
        
        data = {
            'employee_id': self.employee.id,
            'shift_id': self.morning_shift.id,
            'date': tomorrow,
            'status': 'scheduled',
            'notes': 'Regular shift'
        }
        
        response = self.client.post('/api/shifts/schedules/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        schedule = ShiftSchedule.objects.get(id=response.data['id'])
        self.assertEqual(schedule.employee, self.employee)
        self.assertEqual(schedule.shift, self.morning_shift)
        self.assertEqual(schedule.status, 'scheduled')
    
    def test_conflict_prevention(self):
        """Test that scheduling conflicts are prevented"""
        self.client.force_authenticate(user=self.manager)
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create first schedule
        ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=tomorrow,
            created_by=self.manager
        )
        
        # Try to create conflicting schedule
        data = {
            'employee_id': self.employee.id,
            'shift_id': self.night_shift.id,
            'date': tomorrow,
            'status': 'scheduled'
        }
        
        response = self.client.post('/api/shifts/schedules/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has a shift', str(response.data))
    
    def test_shift_start_and_complete(self):
        """Test starting and completing shifts"""
        # Create a schedule for today
        today_schedule = ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=date.today(),
            status='scheduled',
            created_by=self.manager
        )
        
        self.client.force_authenticate(user=self.employee)
        
        # Start shift
        response = self.client.post(f'/api/shifts/schedules/{today_schedule.id}/start/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        today_schedule.refresh_from_db()
        self.assertEqual(today_schedule.status, 'in_progress')
        
        # Complete shift
        response = self.client.post(f'/api/shifts/schedules/{today_schedule.id}/complete/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        today_schedule.refresh_from_db()
        self.assertEqual(today_schedule.status, 'completed')
    
    def test_bulk_shift_creation(self):
        """Test bulk shift creation"""
        self.client.force_authenticate(user=self.manager)
        
        start_date = date.today() + timedelta(days=7)
        end_date = start_date + timedelta(days=6)
        
        data = {
            'employee_ids': [self.employee.id],
            'shift_id': self.morning_shift.id,
            'start_date': start_date,
            'end_date': end_date,
            'notes': 'Weekly schedule'
        }
        
        response = self.client.post('/api/shifts/bulk-create/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Should create 7 schedules (one for each day)
        created_schedules = ShiftSchedule.objects.filter(
            employee=self.employee,
            date__range=[start_date, end_date]
        )
        self.assertEqual(created_schedules.count(), 7)
    
    def test_my_shifts_endpoint(self):
        """Test employee's personal shifts endpoint"""
        # Create some schedules
        ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=date.today(),
            created_by=self.manager
        )
        
        ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.night_shift,
            date=date.today() + timedelta(days=1),
            created_by=self.manager
        )
        
        self.client.force_authenticate(user=self.employee)
        response = self.client.get('/api/shifts/my-shifts/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_shift_calendar_view(self):
        """Test shift calendar functionality"""
        # Create some schedules
        ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=date.today(),
            created_by=self.manager
        )
        
        self.client.force_authenticate(user=self.employee)
        response = self.client.get('/api/shifts/calendar/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('calendar_events', response.data)
        self.assertEqual(len(response.data['calendar_events']), 1)
    
    def test_shift_coverage_report(self):
        """Test shift coverage reporting"""
        today = date.today()
        
        # Create schedules for coverage
        ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=today,
            created_by=self.manager
        )
        
        self.client.force_authenticate(user=self.manager)
        response = self.client.get(f'/api/shifts/coverage-report/?start_date={today}&end_date={today}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('coverage', response.data)
        self.assertEqual(len(response.data['coverage']), 1)
    
    def test_shift_template_functionality(self):
        """Test shift template creation and usage"""
        self.client.force_authenticate(user=self.manager)
        
        # Create template
        data = {
            'name': 'Daily Template',
            'shift_id': self.morning_shift.id,
            'frequency': 'daily',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=7),
            'is_active': True
        }
        
        response = self.client.post('/api/shifts/templates/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        template = ShiftTemplate.objects.get(id=response.data['id'])
        self.assertEqual(template.name, 'Daily Template')
        self.assertEqual(template.frequency, 'daily')
    
    def test_shift_swap_request(self):
        """Test shift swap functionality"""
        # Create a schedule
        schedule = ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=date.today() + timedelta(days=1),
            created_by=self.manager
        )
        
        # Create another employee for swap
        other_employee = User.objects.create_user(
            email='other@test.com', username='other', employee_id='EMP002',
            first_name='Alice', last_name='Brown', role='employee', password='test123'
        )
        
        self.client.force_authenticate(user=self.employee)
        
        data = {
            'schedule_id': schedule.id,
            'target_employee_id': other_employee.id,
            'reason': 'Family emergency'
        }
        
        response = self.client.post('/api/shifts/request-swap/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that swap request was recorded
        schedule.refresh_from_db()
        self.assertIn('Swap requested', schedule.notes)
    
    def test_shift_hours_calculation(self):
        """Test shift duration and hours calculation"""
        # Test regular shift (9am to 5pm = 8 hours - 1 hour break = 7 hours)
        self.assertEqual(self.morning_shift.duration_hours, 8.0)
        self.assertEqual(self.morning_shift.total_hours, 7.0)
        
        # Test overnight shift (9pm to 5am = 8 hours - 1 hour break = 7 hours)
        self.assertEqual(self.night_shift.duration_hours, 8.0)
        self.assertEqual(self.night_shift.total_hours, 7.0)
    
    def test_shift_permissions(self):
        """Test role-based permissions for shift management"""
        # Employee should not be able to create shifts
        self.client.force_authenticate(user=self.employee)
        
        data = {
            'name': 'Test Shift',
            'start_time': '10:00:00',
            'end_time': '18:00:00',
            'break_duration': 60
        }
        
        response = self.client.post('/api/shifts/shifts/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Manager should be able to create shifts
        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/shifts/shifts/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_shift_summary_statistics(self):
        """Test shift summary endpoint"""
        # Create some schedules
        ShiftSchedule.objects.create(
            employee=self.employee,
            shift=self.morning_shift,
            date=date.today(),
            status='scheduled',
            created_by=self.manager
        )
        
        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/shifts/summary/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('today_shifts', response.data)
        self.assertGreater(response.data['today_shifts'], 0)


class ShiftModelTestCase(TestCase):
    """Test cases for Shift Models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com', username='test', employee_id='TEST001',
            first_name='Test', last_name='User', role='employee', password='test123'
        )
        
        self.shift = Shift.objects.create(
            name='Test Shift',
            start_time=time(9, 0),
            end_time=time(17, 0),
            break_duration=60
        )
    
    def test_shift_duration_calculation(self):
        """Test shift duration calculation"""
        # 9am to 5pm = 8 hours
        self.assertEqual(self.shift.duration_hours, 8.0)
        
        # 8 hours - 1 hour break = 7 hours
        self.assertEqual(self.shift.total_hours, 7.0)
    
    def test_overnight_shift_calculation(self):
        """Test overnight shift duration calculation"""
        overnight_shift = Shift.objects.create(
            name='Night Shift',
            start_time=time(23, 0),  # 11 PM
            end_time=time(7, 0),     # 7 AM
            break_duration=60
        )
        
        # 11pm to 7am = 8 hours
        self.assertEqual(overnight_shift.duration_hours, 8.0)
        self.assertEqual(overnight_shift.total_hours, 7.0)
    
    def test_shift_schedule_properties(self):
        """Test shift schedule computed properties"""
        today_schedule = ShiftSchedule.objects.create(
            employee=self.user,
            shift=self.shift,
            date=date.today(),
            created_by=self.user
        )
        
        # Test is_today property
        self.assertTrue(today_schedule.is_today)
        
        # Test is_overdue property
        past_schedule = ShiftSchedule.objects.create(
            employee=self.user,
            shift=self.shift,
            date=date.today() - timedelta(days=1),
            status='scheduled',
            created_by=self.user
        )
        self.assertTrue(past_schedule.is_overdue)
    
    def test_shift_status_transitions(self):
        """Test shift status transition methods"""
        schedule = ShiftSchedule.objects.create(
            employee=self.user,
            shift=self.shift,
            date=date.today(),
            status='scheduled',
            created_by=self.user
        )
        
        # Test starting shift
        success = schedule.start_shift()
        self.assertTrue(success)
        self.assertEqual(schedule.status, 'in_progress')
        
        # Test completing shift
        success = schedule.complete_shift()
        self.assertTrue(success)
        self.assertEqual(schedule.status, 'completed')
        
        # Test cancelling completed shift (should fail)
        success = schedule.cancel_shift()
        self.assertFalse(success)
        self.assertEqual(schedule.status, 'completed')  # Should remain completed
