from django.core.management.base import BaseCommand
from django.utils import timezone
from leave.models import LeaveBalance


class Command(BaseCommand):
    help = 'Allocate annual leave balances for all active employees'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year for leave allocation (default: current year)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating records',
        )

    def handle(self, *args, **options):
        year = options['year']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN MODE - No changes will be made')
            )

        self.stdout.write(f'Allocating leave balances for year {year}...')

        if not dry_run:
            allocated_count = LeaveBalance.allocate_annual_leave(year)
        else:
            # Simulate allocation for dry run
            from users.models import User
            from leave.models import LeaveType
            
            active_users = User.objects.filter(is_active=True)
            active_leave_types = LeaveType.objects.filter(is_active=True, max_days_per_year__gt=0)
            
            allocated_count = 0
            for user in active_users:
                for leave_type in active_leave_types:
                    try:
                        balance = LeaveBalance.objects.get(
                            user=user, leave_type=leave_type, year=year
                        )
                        self.stdout.write(
                            f'  [EXISTS] {user.get_full_name()} - {leave_type.name}: {balance.total_allocated} days'
                        )
                    except LeaveBalance.DoesNotExist:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [CREATE] {user.get_full_name()} - {leave_type.name}: {leave_type.max_days_per_year} days'
                            )
                        )
                        allocated_count += 1

        # Summary
        action = "Would allocate" if dry_run else "Allocated"
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{action} {allocated_count} leave balance records for year {year}'
            )
        )

        if not dry_run and allocated_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    'Leave balances have been allocated. You can now:\n'
                    '1. Review allocations in Django admin\n'
                    '2. Adjust specific employee allocations if needed\n'
                    '3. Employees can now submit leave requests'
                )
            )
        elif allocated_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    'No new leave balances were created. This could mean:\n'
                    '1. Leave balances already exist for this year\n'
                    '2. No active employees found\n'
                    '3. No active leave types with day limits found'
                )
            )
