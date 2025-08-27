from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from datetime import datetime

from .models import LeaveType, LeaveRequest, LeaveBalance
from .serializers import (
	LeaveTypeSerializer, LeaveRequestSerializer, LeaveRequestApprovalSerializer,
	LeaveBalanceSerializer
)
from users.models import User


class IsHRorManager(permissions.BasePermission):
	def has_permission(self, request, view):
		return request.user.is_authenticated and request.user.can_manage_attendance()


# Leave Types (HR/Admin)
class LeaveTypeListCreateView(generics.ListCreateAPIView):
	queryset = LeaveType.objects.all()
	serializer_class = LeaveTypeSerializer
	permission_classes = [permissions.IsAuthenticated, IsHRorManager]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ['name', 'description']
	ordering_fields = ['name', 'max_days_per_year', 'is_active']
	ordering = ['name']


class LeaveTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
	queryset = LeaveType.objects.all()
	serializer_class = LeaveTypeSerializer
	permission_classes = [permissions.IsAuthenticated, IsHRorManager]


# Leave Requests
class LeaveRequestCreateView(generics.CreateAPIView):
	serializer_class = LeaveRequestSerializer
	permission_classes = [permissions.IsAuthenticated]

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)


class LeaveRequestListView(generics.ListAPIView):
	serializer_class = LeaveRequestSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
	filterset_fields = ['leave_type', 'status', 'start_date', 'end_date']
	ordering_fields = ['start_date', 'end_date', 'created_at']
	ordering = ['-created_at']

	def get_queryset(self):
		user = self.request.user
		if user.can_manage_attendance():
			qs = LeaveRequest.objects.select_related('user', 'leave_type')
			user_id = self.request.query_params.get('user_id')
			if user_id:
				qs = qs.filter(user_id=user_id)
			return qs
		return LeaveRequest.objects.filter(user=user).select_related('leave_type')


class LeaveRequestDetailView(generics.RetrieveAPIView):
	serializer_class = LeaveRequestSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		user = self.request.user
		if user.can_manage_attendance():
			return LeaveRequest.objects.all()
		return LeaveRequest.objects.filter(user=user)


class LeaveApprovalView(APIView):
	permission_classes = [permissions.IsAuthenticated, IsHRorManager]

	def post(self, request, pk):
		try:
			leave = LeaveRequest.objects.get(pk=pk)
		except LeaveRequest.DoesNotExist:
			return Response({'error': 'Leave request not found'}, status=404)

		serializer = LeaveRequestApprovalSerializer(data=request.data)
		if serializer.is_valid():
			leave.status = serializer.validated_data['status']
			leave.approval_notes = serializer.validated_data.get('approval_notes', '')
			leave.approved_by = request.user
			leave.save()
			return Response({'message': f"Leave {leave.status} successfully", 'leave': LeaveRequestSerializer(leave).data})
		return Response(serializer.errors, status=400)


# Leave Balances
class LeaveBalanceListView(generics.ListAPIView):
	serializer_class = LeaveBalanceSerializer
	permission_classes = [permissions.IsAuthenticated]
	filter_backends = [DjangoFilterBackend]
	filterset_fields = ['user', 'leave_type', 'year']

	def get_queryset(self):
		user = self.request.user
		if user.can_manage_attendance():
			qs = LeaveBalance.objects.select_related('user', 'leave_type')
			user_id = self.request.query_params.get('user_id')
			if user_id:
				qs = qs.filter(user_id=user_id)
			return qs
		return LeaveBalance.objects.filter(user=user).select_related('leave_type')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_leave_requests(request):
	qs = LeaveRequest.objects.filter(user=request.user).select_related('leave_type')
	return Response(LeaveRequestSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsHRorManager])
def allocate_leave_balance(request):
	user_id = request.data.get('user')
	leave_type_id = request.data.get('leave_type')
	year = request.data.get('year')
	total_allocated = request.data.get('total_allocated')
	if not all([user_id, leave_type_id, year, total_allocated]):
		return Response({'error': 'user, leave_type, year, total_allocated are required'}, status=400)
	lb, created = LeaveBalance.objects.get_or_create(
		user_id=user_id, leave_type_id=leave_type_id, year=year,
		defaults={'total_allocated': total_allocated}
	)
	if not created:
		lb.total_allocated = total_allocated
		lb.save()
	return Response({'message': 'Leave balance set', 'balance': LeaveBalanceSerializer(lb).data})
