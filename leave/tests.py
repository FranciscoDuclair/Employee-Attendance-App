from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from .models import LeaveType, LeaveRequest, LeaveBalance

User = get_user_model()


class LeaveSetupMixin:
	def create_users(self):
		self.employee = User.objects.create_user(
			email='emp@company.com', username='empuser', employee_id='EMP001',
			first_name='Emp', last_name='User', role='employee'
		)
		self.hr = User.objects.create_user(
			email='hr@company.com', username='hruser', employee_id='HR001',
			first_name='HR', last_name='User', role='hr'
		)
		self.manager = User.objects.create_user(
			email='mgr@company.com', username='mgruser', employee_id='MGR001',
			first_name='Mgr', last_name='User', role='manager'
		)
		self.emp_token = str(RefreshToken.for_user(self.employee).access_token)
		self.hr_token = str(RefreshToken.for_user(self.hr).access_token)
		self.mgr_token = str(RefreshToken.for_user(self.manager).access_token)

	def create_leave_type(self, requires_approval=True):
		return LeaveType.objects.create(
			name='Annual Leave', max_days_per_year=20,
			requires_approval=requires_approval, is_paid=True, is_active=True
		)


class LeaveAPITest(APITestCase, LeaveSetupMixin):
	def setUp(self):
		self.create_users()
		self.leave_type = self.create_leave_type(requires_approval=True)

	def test_employee_create_leave_request(self):
		url = reverse('leave_request_create')
		data = {
			'leave_type': self.leave_type.id,
			'start_date': date.today(),
			'end_date': date.today() + timedelta(days=2),
			'reason': 'Vacation'
		}
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.emp_token}')
		resp = self.client.post(url, data)
		self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
		self.assertEqual(resp.data['status'], 'pending')

	def test_hr_approve_leave_request(self):
		# Create request
		lr = LeaveRequest.objects.create(
			user=self.employee, leave_type=self.leave_type,
			start_date=date.today(), end_date=date.today() + timedelta(days=1),
			reason='Family'
		)
		url = reverse('leave_request_approve', kwargs={'pk': lr.id})
		data = {'status': 'approved', 'approval_notes': 'Enjoy'}
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
		resp = self.client.post(url, data)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(resp.data['leave']['status'], 'approved')

	def test_employee_cannot_approve(self):
		lr = LeaveRequest.objects.create(
			user=self.employee, leave_type=self.leave_type,
			start_date=date.today(), end_date=date.today(), reason='x'
		)
		url = reverse('leave_request_approve', kwargs={'pk': lr.id})
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.emp_token}')
		resp = self.client.post(url, {'status': 'approved'})
		self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

	def test_leave_balances_allocation(self):
		url = reverse('allocate_leave_balance')
		payload = {
			'user': self.employee.id,
			'leave_type': self.leave_type.id,
			'year': date.today().year,
			'total_allocated': 20
		}
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
		resp = self.client.post(url, payload)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(resp.data['balance']['total_allocated'], 20)

	def test_leave_requests_list_employee(self):
		LeaveRequest.objects.create(user=self.employee, leave_type=self.leave_type,
			start_date=date.today(), end_date=date.today(), reason='x')
		url = reverse('leave_requests')
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.emp_token}')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, status.HTTP_200_OK)
		self.assertEqual(len(resp.data['results']), 1)

	def test_leave_types_crud_permissions(self):
		# Employee should not create
		url = reverse('leave_types')
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.emp_token}')
		resp = self.client.post(url, {'name': 'Sick', 'max_days_per_year': 10, 'requires_approval': True, 'is_paid': True, 'is_active': True})
		self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
		# HR can create
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.hr_token}')
		resp = self.client.post(url, {'name': 'Sick', 'max_days_per_year': 10, 'requires_approval': True, 'is_paid': True, 'is_active': True})
		self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
