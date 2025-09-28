from django.urls import path
from . import views

urlpatterns = [
    # Attendance records
    path('', views.AttendanceListView.as_view(), name='attendance-list'),
    
    # Check-in/out endpoints with face verification
    path('checkin/', views.CheckInView.as_view(), name='checkin'),
    path('checkout/', views.CheckOutView.as_view(), name='checkout'),
    
    # Today's attendance
    path('today/', views.today_attendance, name='today-attendance'),
    
    # Face recognition management
    path('face-setup/', views.setup_face_recognition, name='face-setup'),
    path('face-status/', views.face_recognition_status, name='face-status'),
    path('face-remove/', views.remove_face_recognition, name='face-remove'),
    
    # Deprecated face recognition endpoints (kept for backward compatibility)
    path('face-checkin/', views.face_recognition_checkin, name='face-checkin-deprecated'),
    path('face-checkout/', views.face_recognition_checkout, name='face-checkout-deprecated'),
    
    # Attendance summary and analytics
    path('summary/', views.attendance_summary, name='attendance-summary'),
    path('analytics/', views.attendance_analytics, name='attendance-analytics'),
]
