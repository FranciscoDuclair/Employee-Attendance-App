#!/usr/bin/env python
"""
Database setup script for Employee Attendance Platform
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def setup_database():
    """Setup the database with migrations and create superuser"""
    print("Setting up Employee Attendance Platform Database...")
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_platform.settings')
    django.setup()
    
    try:
        # Run migrations
        print("Running migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations completed successfully!")
        
        # Create superuser
        print("Creating superuser...")
        from users.models import User
        
        # Check if superuser already exists
        if not User.objects.filter(email='admin@company.com').exists():
            User.objects.create_superuser(
                email='admin@company.com',
                username='admin',
                employee_id='EMP001',
                first_name='Admin',
                last_name='User',
                role='hr'
            )
            print("✅ Superuser created successfully!")
            print("   Email: admin@company.com")
            print("   Username: admin")
            print("   Employee ID: EMP001")
        else:
            print("ℹ️  Superuser already exists!")
        
        # Create some sample data
        print("Creating sample data...")
        create_sample_data()
        
        print("\n🎉 Database setup completed successfully!")
        print("\nYou can now:")
        print("1. Run the development server: python manage.py runserver")
        print("2. Access admin panel: http://localhost:8000/admin/")
        print("3. View API docs: http://localhost:8000/api/docs/")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        sys.exit(1)

def create_sample_data():
    """Create sample data for testing"""
    from users.models import User
    from leave.models import LeaveType
    from shifts.models import Shift
    
    # Create sample leave types
    leave_types = [
        ('Annual Leave', 'Annual vacation leave', 21, True, True),
        ('Sick Leave', 'Medical leave', 10, True, True),
        ('Personal Leave', 'Personal time off', 5, True, False),
        ('Emergency Leave', 'Emergency situations', 3, False, True),
    ]
    
    for name, desc, max_days, requires_approval, is_paid in leave_types:
        LeaveType.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'max_days_per_year': max_days,
                'requires_approval': requires_approval,
                'is_paid': is_paid
            }
        )
    
    # Create sample shifts
    shifts = [
        ('Morning Shift', '9:00 AM - 5:00 PM', '09:00', '17:00', 60),
        ('Evening Shift', '2:00 PM - 10:00 PM', '14:00', '22:00', 60),
        ('Night Shift', '10:00 PM - 6:00 AM', '22:00', '06:00', 60),
    ]
    
    for name, desc, start, end, break_duration in shifts:
        Shift.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'start_time': start,
                'end_time': end,
                'break_duration': break_duration
            }
        )
    
    print("✅ Sample data created successfully!")

if __name__ == '__main__':
    setup_database()
