from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CheckInView, CheckOutView, FaceRecognitionView, ManualAttendanceView,
    AttendanceHistoryView, AttendanceStatsView, AttendanceListView,
    AttendanceDetailView, today_attendance, bulk_attendance_approval
)

# Create router for ViewSets
router = DefaultRouter()

urlpatterns = [
    # Basic attendance endpoints
    path('check-in/', CheckInView.as_view(), name='check_in'),
    path('check-out/', CheckOutView.as_view(), name='check_out'),
    path('face-recognition/', FaceRecognitionView.as_view(), name='face_recognition'),
    
    # Manual attendance (HR/Admin only)
    path('manual/', ManualAttendanceView.as_view(), name='manual_attendance'),
    
    # History and statistics
    path('history/', AttendanceHistoryView.as_view(), name='attendance_history'),
    path('stats/', AttendanceStatsView.as_view(), name='attendance_stats'),
    path('today/', today_attendance, name='today_attendance'),
    
    # Management endpoints (HR/Admin only)
    path('list/', AttendanceListView.as_view(), name='attendance_list'),
    path('<int:pk>/', AttendanceDetailView.as_view(), name='attendance_detail'),
    path('bulk-approval/', bulk_attendance_approval, name='bulk_approval'),
    
    # Include router URLs
    path('', include(router.urls)),
]
