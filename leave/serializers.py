from rest_framework import serializers
from django.utils import timezone
from datetime import date
from .models import LeaveType, LeaveRequest, LeaveBalance
from users.models import User


class LeaveTypeSerializer(serializers.ModelSerializer):
	class Meta:
		model = LeaveType
		fields = ['id', 'name', 'description', 'max_days_per_year', 'requires_approval', 'is_paid', 'is_active']


class LeaveRequestSerializer(serializers.ModelSerializer):
	user_name = serializers.CharField(source='user.get_full_name', read_only=True)
	employee_id = serializers.CharField(source='user.employee_id', read_only=True)
	leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

	class Meta:
		model = LeaveRequest
		fields = [
			'id', 'user', 'user_name', 'employee_id', 'leave_type', 'leave_type_name',
			'start_date', 'end_date', 'total_days', 'reason', 'status', 'approved_by',
			'approval_notes', 'emergency_contact', 'emergency_phone', 'created_at', 'updated_at'
		]
		read_only_fields = ['total_days', 'status', 'approved_by', 'created_at', 'updated_at']

	def validate(self, attrs):
		start = attrs.get('start_date')
		end = attrs.get('end_date')
		if start and end and start > end:
			raise serializers.ValidationError('Start date must be before end date')
		return attrs

	def create(self, validated_data):
		# Default status based on leave type
		leave_type = validated_data['leave_type']
		if leave_type.requires_approval:
			validated_data['status'] = 'pending'
		else:
			validated_data['status'] = 'approved'
		return super().create(validated_data)


class LeaveRequestApprovalSerializer(serializers.ModelSerializer):
	class Meta:
		model = LeaveRequest
		fields = ['status', 'approval_notes']

	def validate_status(self, value):
		if value not in ['approved', 'rejected']:
			raise serializers.ValidationError('Status must be approved or rejected')
		return value


class LeaveBalanceSerializer(serializers.ModelSerializer):
	user_name = serializers.CharField(source='user.get_full_name', read_only=True)
	leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

	class Meta:
		model = LeaveBalance
		fields = [
			'id', 'user', 'user_name', 'leave_type', 'leave_type_name',
			'year', 'total_allocated', 'used_days', 'remaining_days'
		]
		read_only_fields = ['remaining_days']
