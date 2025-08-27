from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView, UserRegistrationView, UserProfileView,
    ChangePasswordView, UserListView, UserDetailView, UserCreateView,
    assign_manager, user_stats, toggle_user_status
)

# Create router for ViewSets
router = DefaultRouter()

urlpatterns = [
    # Authentication URLs
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', UserRegistrationView.as_view(), name='user_register'),
    
    # User profile URLs
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User management URLs (HR/Admin only)
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:user_id>/assign-manager/', assign_manager, name='assign_manager'),
    path('users/<int:user_id>/toggle-status/', toggle_user_status, name='toggle_user_status'),
    path('stats/', user_stats, name='user_stats'),
    
    # Include router URLs
    path('', include(router.urls)),
]
