import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Create a timestamped backup of the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old backups (keep last 10)',
        )

    def handle(self, *args, **options):
        try:
            # Create backup using django-dbbackup
            self.stdout.write('Creating database backup...')
            call_command('dbbackup', '--clean')  # --clean removes old backups
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Database backup created successfully at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                )
            )
            
            # Optional: Also backup media files
            backup_dir = getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups')
            self.stdout.write(f'Backups stored in: {backup_dir}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Backup failed: {str(e)}')
            )
