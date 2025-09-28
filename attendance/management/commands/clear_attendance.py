from django.core.management.base import BaseCommand
from django.conf import settings
from attendance.models import Attendance
import os
import shutil

class Command(BaseCommand):
    help = 'Clear all attendance records and associated face images'

    def handle(self, *args, **options):
        # Ask for confirmation
        confirm = input('WARNING: This will delete ALL attendance records and associated face images. Continue? (yes/no): ')
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Operation cancelled.'))
            return
            
        try:
            # Delete all attendance records
            count, _ = Attendance.objects.all().delete()
            
            # Delete face images
            faces_dir = os.path.join(settings.MEDIA_ROOT, 'attendance/faces')
            if os.path.exists(faces_dir):
                shutil.rmtree(faces_dir)
                os.makedirs(faces_dir, exist_ok=True)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} attendance records and associated face images.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error clearing attendance data: {str(e)}'))
