from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.db.models import Q
try:
    from django_filters.rest_framework import DjangoFilterBackend
except ImportError:
    DjangoFilterBackend = None
from rest_framework import filters

from .models import User
from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserUpdateSerializer,
    LoginSerializer, ChangePasswordSerializer, UserListSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token view with additional user data"""
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Get user data
            email = request.data.get('email')
            user = User.objects.get(email=email)
            user_data = UserSerializer(user).data
            
            # Add user data to response
            response.data['user'] = user_data
        return response


class UserRegistrationView(APIView):
    """User registration endpoint"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """User profile management"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Update current user profile"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': UserSerializer(request.user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """List all users (HR/Admin only)"""
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter] if DjangoFilterBackend else [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'department', 'is_active'] if DjangoFilterBackend else []
    search_fields = ['first_name', 'last_name', 'employee_id', 'email']
    ordering_fields = ['created_at', 'employee_id', 'first_name']
    ordering = ['employee_id']
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['hr', 'manager']:
            return User.objects.all()
        else:
            # Regular employees can only see themselves
            return User.objects.filter(id=user.id)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """User detail view (HR/Admin only)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['hr', 'manager']:
            return User.objects.all()
        else:
            # Regular employees can only see themselves
            return User.objects.filter(id=user.id)
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        
        # Check if user can access this profile
        if user.role not in ['hr', 'manager'] and obj.id != user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only view your own profile.")
        
        return obj


class UserCreateView(generics.CreateAPIView):
    """Create new user (HR/Admin only)"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ['hr', 'manager']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only HR and Managers can create users.")
        
        # Set manager if not specified and current user is a manager
        if user.role == 'manager' and 'manager' not in serializer.validated_data:
            serializer.validated_data['manager'] = user
        
        serializer.save()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def assign_manager(request, user_id):
    """Assign manager to user (HR/Admin only)"""
    if request.user.role not in ['hr', 'manager']:
        return Response(
            {'error': 'Only HR and Managers can assign managers.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        manager_id = request.data.get('manager_id')
        
        if manager_id:
            manager = User.objects.get(id=manager_id)
            if manager.role not in ['hr', 'manager']:
                return Response(
                    {'error': 'Manager must have HR or Manager role.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.manager = manager
        else:
            user.manager = None
        
        user.save()
        return Response({
            'message': 'Manager assigned successfully',
            'user': UserSerializer(user).data
        })
    
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get user statistics (HR/Admin only)"""
    if request.user.role not in ['hr', 'manager']:
        return Response(
            {'error': 'Only HR and Managers can view statistics.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'employees': User.objects.filter(role='employee').count(),
        'managers': User.objects.filter(role='manager').count(),
        'hr_users': User.objects.filter(role='hr').count(),
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def toggle_user_status(request, user_id):
    """Toggle user active status (HR/Admin only)"""
    if request.user.role not in ['hr', 'manager']:
        return Response(
            {'error': 'Only HR and Managers can toggle user status.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        
        return Response({
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'user': UserSerializer(user).data
        })
    
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )