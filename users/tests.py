from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model"""
    
    def setUp(self):
        self.user_data = {
            'email': 'test@company.com',
            'username': 'testuser',
            'employee_id': 'EMP001',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'employee',
            'department': 'IT',
            'position': 'Developer'
        }
    
    def test_create_user(self):
        """Test user creation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.email, 'test@company.com')
        self.assertEqual(user.employee_id, 'EMP001')
        self.assertEqual(user.role, 'employee')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_create_superuser(self):
        """Test superuser creation"""
        user = User.objects.create_superuser(**self.user_data)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Test User')
    
    def test_role_permissions(self):
        """Test role-based permissions"""
        # Test employee
        employee = User.objects.create_user(**self.user_data)
        self.assertFalse(employee.is_hr_or_admin())
        self.assertFalse(employee.can_manage_attendance())
        self.assertFalse(employee.can_approve_leave())
        
        # Test HR
        hr_data = self.user_data.copy()
        hr_data.update({'email': 'hr@company.com', 'role': 'hr'})
        hr_user = User.objects.create_user(**hr_data)
        self.assertTrue(hr_user.is_hr_or_admin())
        self.assertTrue(hr_user.can_manage_attendance())
        self.assertTrue(hr_user.can_approve_leave())


class AuthenticationAPITest(APITestCase):
    """Test authentication API endpoints"""
    
    def setUp(self):
        self.user_data = {
            'email': 'test@company.com',
            'username': 'testuser',
            'employee_id': 'EMP001',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'employee',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
    
    def test_user_registration(self):
        """Test user registration"""
        url = reverse('user_register')
        data = {
            'email': 'newuser@company.com',
            'username': 'newuser',
            'employee_id': 'EMP002',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'employee',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('tokens' in response.data)
        self.assertTrue('user' in response.data)
    
    def test_user_login(self):
        """Test user login"""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@company.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('access' in response.data)
        self.assertTrue('refresh' in response.data)
        self.assertTrue('user' in response.data)
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        url = reverse('token_obtain_pair')
        data = {
            'email': 'test@company.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_profile(self):
        """Test user profile endpoint"""
        url = reverse('user_profile')
        
        # Test without authentication
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test with authentication
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_change_password(self):
        """Test password change"""
        url = reverse('change_password')
        data = {
            'old_password': 'testpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))


class UserManagementAPITest(APITestCase):
    """Test user management API endpoints"""
    
    def setUp(self):
        self.hr_user = User.objects.create_user(
            email='hr@company.com',
            username='hruser',
            employee_id='HR001',
            first_name='HR',
            last_name='User',
            role='hr',
            password='hrpass123'
        )
        
        self.employee = User.objects.create_user(
            email='emp@company.com',
            username='empuser',
            employee_id='EMP001',
            first_name='Employee',
            last_name='User',
            role='employee',
            password='emppass123'
        )
    
    def test_user_list_hr_access(self):
        """Test HR can access user list"""
        url = reverse('user_list')
        self.client.force_authenticate(user=self.hr_user)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # HR + Employee
    
    def test_user_list_employee_access(self):
        """Test employee can only see themselves"""
        url = reverse('user_list')
        self.client.force_authenticate(user=self.employee)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only themselves
    
    def test_user_stats_hr_access(self):
        """Test HR can access user statistics"""
        url = reverse('user_stats')
        self.client.force_authenticate(user=self.hr_user)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_users'], 2)
        self.assertEqual(response.data['hr_users'], 1)
        self.assertEqual(response.data['employees'], 1)
    
    def test_user_stats_employee_access(self):
        """Test employee cannot access user statistics"""
        url = reverse('user_stats')
        self.client.force_authenticate(user=self.employee)
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
