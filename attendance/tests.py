from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime, timedelta

from .models import Attendance

User = get_user_model()


class AttendanceModelTest(TestCase):
    """Test Attendance model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@company.com',
            username='testuser',
            employee_id='EMP001',
            first_name='Test',
            last_name='User',
            role='employee'
        )
    
    def test_attendance_creation(self):
        """Test attendance record creation"""
        now = timezone.now()
        attendance = Attendance.objects.create(
            user=self.user,
            date=now.date(),
            check_in_time=now,
            attendance_type='check_in',
            status='present'
        )
        
        self.assertEqual(attendance.user, self.user)
        self.assertEqual(attendance.attendance_type, 'check_in')
        self.assertEqual(attendance.status, 'present')
        self.assertTrue(attendance.face_verified is False)
    
    def test_hours_worked_calculation(self):
        """Test hours worked calculation"""
        checkin_time = timezone.now()
        checkout_time = checkin_time + timedelta(hours=8)
        
        checkin = Attendance.objects.create(
            user=self.user,
            date=checkin_time.date(),
            check_in_time=checkin_time,
            attendance_type='check_in',
            status='present'
        )
        
        checkout = Attendance.objects.create(
            user=self.user,
            date=checkout_time.date(),
            check_out_time=checkout_time,
            attendance_type='check_out',
            status='present'
        )
        
        self.assertEqual(checkout.hours_worked, 8.0)
    
    def test_is_late_calculation(self):
        """Test late arrival detection"""
        late_time = timezone.now().replace(hour=9, minute=30, second=0, microsecond=0)
        
        attendance = Attendance.objects.create(
            user=self.user,
            date=late_time.date(),
            check_in_time=late_time,
            attendance_type='check_in',
            status='present'
        )
        
        self.assertTrue(attendance.is_late)


class AttendanceAPITest(APITestCase):
    """Test attendance API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@company.com',
            username='testuser',
            employee_id='EMP001',
            first_name='Test',
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
        
        # Get JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        refresh_hr = RefreshToken.for_user(self.hr_user)
        self.hr_access_token = str(refresh_hr.access_token)
    
    def test_check_in(self):
        """Test check-in endpoint"""
        url = reverse('check_in')
        data = {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'notes': 'Arrived at work'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Check-in successful')
        self.assertTrue('attendance' in response.data)
    
    def test_check_out(self):
        """Test check-out endpoint"""
        # First check in
        checkin_url = reverse('check_in')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        self.client.post(checkin_url, {})
        
        # Then check out
        checkout_url = reverse('check_out')
        data = {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'notes': 'Leaving work'
        }
        
        response = self.client.post(checkout_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Check-out successful')
    
    def test_check_out_without_checkin(self):
        """Test check-out without prior check-in"""
        url = reverse('check_out')
        data = {
            'latitude': '40.7128',
            'longitude': '-74.0060'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You must check in before checking out')
    
    def test_duplicate_checkin(self):
        """Test duplicate check-in prevention"""
        url = reverse('check_in')
        data = {'notes': 'First check-in'}
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # First check-in
        response1 = self.client.post(url, data)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Second check-in (should fail)
        response2 = self.client.post(url, data)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_attendance_history(self):
        """Test attendance history endpoint"""
        # Create some attendance records
        today = timezone.now().date()
        Attendance.objects.create(
            user=self.user,
            date=today,
            check_in_time=timezone.now(),
            attendance_type='check_in',
            status='present'
        )
        
        url = reverse('attendance_history')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_today_attendance(self):
        """Test today's attendance status"""
        url = reverse('today_attendance')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['checked_in'])
        self.assertFalse(response.data['checked_out'])
        self.assertEqual(response.data['status'], 'absent')
    
    def test_manual_attendance_hr_access(self):
        """Test HR can create manual attendance"""
        url = reverse('manual_attendance')
        data = {
            'user': self.user.id,
            'date': timezone.now().date(),
            'check_in_time': timezone.now(),
            'attendance_type': 'check_in',
            'status': 'present',
            'notes': 'Manual entry'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_access_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'Manual attendance record created successfully')
    
    def test_manual_attendance_employee_access(self):
        """Test employee cannot create manual attendance"""
        url = reverse('manual_attendance')
        data = {
            'user': self.user.id,
            'date': timezone.now().date(),
            'check_in_time': timezone.now(),
            'attendance_type': 'check_in',
            'status': 'present'
        }
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Only HR and Managers can create manual attendance records')
    
    def test_attendance_stats(self):
        """Test attendance statistics"""
        # Create attendance records for the last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        for i in range(5):  # 5 working days
            date = start_date + timedelta(days=i)
            if date.weekday() < 5:  # Weekdays only
                Attendance.objects.create(
                    user=self.user,
                    date=date,
                    check_in_time=timezone.now(),
                    attendance_type='check_in',
                    status='present'
                )
        
        url = reverse('attendance_stats')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['present_days'], 5)
        self.assertTrue('total_hours' in response.data)
        self.assertTrue('punctuality_rate' in response.data)


class AttendancePermissionsTest(APITestCase):
    """Test attendance permissions and access control"""
    
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
    
    def test_attendance_list_employee_access(self):
        """Test employee cannot access attendance list"""
        url = reverse('attendance_list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.employee_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)  # Empty results
    
    def test_attendance_list_manager_access(self):
        """Test manager can access attendance list"""
        url = reverse('attendance_list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.manager_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_attendance_list_hr_access(self):
        """Test HR can access attendance list"""
        url = reverse('attendance_list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
