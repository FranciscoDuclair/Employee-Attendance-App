from rest_framework import serializers
from django.utils import timezone
from datetime import date, timedelta
from django.core.exceptions import ValidationError as DjangoValidationError
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
	approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
	calculated_days = serializers.SerializerMethodField()

	class Meta:
		model = LeaveRequest
		fields = [
			'id', 'user', 'user_name', 'employee_id', 'leave_type', 'leave_type_name',
			'start_date', 'end_date', 'total_days', 'calculated_days', 'reason', 'status', 
			'approved_by', 'approved_by_name', 'approved_at', 'approval_notes', 
			'emergency_contact', 'emergency_phone', 'created_at', 'updated_at'
		]
		read_only_fields = ['total_days', 'status', 'approved_by', 'approved_at', 'created_at', 'updated_at']

	def get_calculated_days(self, obj):
		"""Calculate working days for display purposes"""
		if obj.start_date and obj.end_date:
			current_date = obj.start_date
			total_days = 0
			while current_date <= obj.end_date:
				if current_date.weekday() < 5:  # Monday to Friday
					total_days += 1
				current_date += timedelta(days=1)
			return total_days
		return 0

	def validate(self, attrs):
		start_date = attrs.get('start_date')
		end_date = attrs.get('end_date')
		leave_type = attrs.get('leave_type')
		user = self.context['request'].user if 'request' in self.context else None

		# Basic date validation
		if start_date and end_date:
			if start_date > end_date:
				raise serializers.ValidationError('Start date must be before end date')
			
			# Prevent requesting leave for past dates (except for updates)
			if not self.instance and start_date < date.today():
				raise serializers.ValidationError('Cannot request leave for past dates')
			
			# Calculate working days for validation
			calculated_days = self.get_calculated_days(type('obj', (), attrs)())
			if calculated_days == 0:
				raise serializers.ValidationError('Leave request must include at least one working day')

		# Additional validation for leave balance if user is available
		if user and leave_type and start_date and end_date:
			calculated_days = self.get_calculated_days(type('obj', (), attrs)())
			
			try:
				balance = LeaveBalance.objects.get(
					user=user,
					leave_type=leave_type,
					year=start_date.year
				)
				if balance.remaining_days < calculated_days:
					raise serializers.ValidationError(
						f'Insufficient leave balance. Available: {balance.remaining_days} days, '
						f'Requested: {calculated_days} days'
					)
			except LeaveBalance.DoesNotExist:
				# If no balance exists and leave type has limits, check max allowed
				if leave_type.max_days_per_year > 0 and calculated_days > leave_type.max_days_per_year:
					raise serializers.ValidationError(
						f'Requested days ({calculated_days}) exceed maximum allowed '
						f'({leave_type.max_days_per_year}) for {leave_type.name}'
					)

		return attrs

	def create(self, validated_data):
		# Set default status based on leave type approval requirement
		leave_type = validated_data['leave_type']
		if leave_type.requires_approval:
			validated_data['status'] = 'pending'
		else:
			validated_data['status'] = 'approved'
			validated_data['approved_at'] = timezone.now()
		
		try:
			return super().create(validated_data)
		except DjangoValidationError as e:
			raise serializers.ValidationError(str(e))


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
