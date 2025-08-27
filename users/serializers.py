from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'username', 'employee_id', 'first_name', 'last_name',
            'role', 'phone_number', 'department', 'position', 'hire_date',
            'password', 'password_confirm'
        ]
        extra_kwargs = {
            'employee_id': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def validate_employee_id(self, value):
        if User.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError("Employee ID already exists.")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'employee_id', 'first_name', 'last_name',
            'full_name', 'role', 'phone_number', 'department', 'position',
            'hire_date', 'is_active', 'profile_picture', 'manager', 'manager_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'department',
            'position', 'profile_picture'
        ]


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password.')
        
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list (minimal data)"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'employee_id', 'full_name', 'email', 'role',
            'department', 'position', 'is_active'
        ]
