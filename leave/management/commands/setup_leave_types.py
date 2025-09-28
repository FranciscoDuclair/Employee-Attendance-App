from django.core.management.base import BaseCommand
from leave.models import LeaveType


class Command(BaseCommand):
    help = 'Setup default leave types for the organization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if leave types already exist',
        )

    def handle(self, *args, **options):
        default_leave_types = [
            {
                'name': 'Annual Leave',
                'description': 'Yearly vacation leave allocation',
                'max_days_per_year': 21,
                'requires_approval': True,
                'is_paid': True,
                'is_active': True
            },
            {
                'name': 'Sick Leave',
                'description': 'Medical leave for illness or health issues',
                'max_days_per_year': 12,
                'requires_approval': False,  # Auto-approved for emergencies
                'is_paid': True,
                'is_active': True
            },
            {
                'name': 'Personal Leave',
                'description': 'Personal time off for personal matters',
                'max_days_per_year': 5,
                'requires_approval': True,
                'is_paid': False,
                'is_active': True
            },
            {
                'name': 'Maternity Leave',
                'description': 'Maternity leave for new mothers',
                'max_days_per_year': 90,
                'requires_approval': True,
                'is_paid': True,
                'is_active': True
            },
            {
                'name': 'Paternity Leave',
                'description': 'Paternity leave for new fathers',
                'max_days_per_year': 14,
                'requires_approval': True,
                'is_paid': True,
                'is_active': True
            },
            {
                'name': 'Emergency Leave',
                'description': 'Emergency leave for urgent family matters',
                'max_days_per_year': 3,
                'requires_approval': False,  # Auto-approved for emergencies
                'is_paid': False,
                'is_active': True
            },
            {
                'name': 'Bereavement Leave',
                'description': 'Leave for funeral or bereavement purposes',
                'max_days_per_year': 5,
                'requires_approval': False,  # Auto-approved
                'is_paid': True,
                'is_active': True
            },
            {
                'name': 'Study Leave',
                'description': 'Leave for educational or training purposes',
                'max_days_per_year': 10,
                'requires_approval': True,
                'is_paid': False,
                'is_active': True
            }
        ]

        created_count = 0
        updated_count = 0

        for leave_data in default_leave_types:
            leave_type, created = LeaveType.objects.get_or_create(
                name=leave_data['name'],
                defaults=leave_data
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created leave type: {leave_type.name}')
                )
            elif options['force']:
                # Update existing leave type
                for key, value in leave_data.items():
                    if key != 'name':  # Don't update the name
                        setattr(leave_type, key, value)
                leave_type.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated leave type: {leave_type.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Leave type already exists: {leave_type.name}')
                )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSetup complete!\n'
                f'Created: {created_count} leave types\n'
                f'Updated: {updated_count} leave types\n'
                f'Total leave types: {LeaveType.objects.count()}'
            )
        )

        if created_count > 0 or updated_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    '\nNext steps:\n'
                    '1. Run: python manage.py allocate_annual_leave\n'
                    '2. Configure specific leave allocations per employee if needed\n'
                    '3. Review and adjust leave policies in Django admin'
                )
            )
