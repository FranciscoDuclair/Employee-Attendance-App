from django.core.management.base import BaseCommand
from shifts.models import Shift


class Command(BaseCommand):
    help = 'Setup default shift types for the organization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if shifts already exist',
        )

    def handle(self, *args, **options):
        default_shifts = [
            {
                'name': 'Morning Shift',
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'break_duration': 60,
                'is_active': True
            },
            {
                'name': 'Afternoon Shift',
                'start_time': '13:00:00',
                'end_time': '21:00:00',
                'break_duration': 60,
                'is_active': True
            },
            {
                'name': 'Night Shift',
                'start_time': '21:00:00',
                'end_time': '05:00:00',
                'break_duration': 60,
                'is_active': True
            },
            {
                'name': 'Weekend Shift',
                'start_time': '10:00:00',
                'end_time': '18:00:00',
                'break_duration': 60,
                'is_active': True
            },
            {
                'name': 'Part-time Morning',
                'start_time': '09:00:00',
                'end_time': '13:00:00',
                'break_duration': 30,
                'is_active': True
            },
            {
                'name': 'Part-time Afternoon',
                'start_time': '14:00:00',
                'end_time': '18:00:00',
                'break_duration': 30,
                'is_active': True
            },
            {
                'name': 'Flexible Shift',
                'start_time': '08:00:00',
                'end_time': '16:00:00',
                'break_duration': 60,
                'is_active': True
            },
            {
                'name': 'On-Call Shift',
                'start_time': '00:00:00',
                'end_time': '23:59:00',
                'break_duration': 0,
                'is_active': True
            }
        ]

        created_count = 0
        updated_count = 0

        for shift_data in default_shifts:
            shift, created = Shift.objects.get_or_create(
                name=shift_data['name'],
                defaults=shift_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created shift: {shift.name}')
                )
            elif options['force']:
                # Update existing shift
                for key, value in shift_data.items():
                    if key != 'name':  # Don't update the name
                        setattr(shift, key, value)
                shift.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated shift: {shift.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Shift already exists: {shift.name}')
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSetup complete!\n'
                f'Created: {created_count} shifts\n'
                f'Updated: {updated_count} shifts\n'
                f'Total shifts: {Shift.objects.count()}'
            )
        )

        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\nNext steps:\n'
                    '1. Review shift configurations in Django admin\n'
                    '2. Create shift templates for recurring schedules\n'
                    '3. Assign shifts to employees using the API or admin panel'
                )
            )
