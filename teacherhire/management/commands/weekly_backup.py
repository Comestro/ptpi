"""
Management command for automated weekly database backups.

This command should be scheduled using cron or system scheduler:

# Linux/Mac (crontab -e):
# Every Sunday at 2:00 AM:
0 2 * * 0 cd /path/to/project && /path/to/python manage.py weekly_backup

# Windows Task Scheduler:
# Create a task that runs weekly and executes:
# python manage.py weekly_backup
"""

from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Automated weekly database backup (for cron/scheduler)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-media',
            action='store_true',
            help='Also backup media files',
        )

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.stdout.write('=' * 60)
        self.stdout.write(f'WEEKLY BACKUP STARTED: {timestamp}')
        self.stdout.write('=' * 60)
        
        try:
            # Backup database
            self.stdout.write('\n[1/2] Backing up database...')
            call_command('dbbackup', '--clean')
            self.stdout.write(self.style.SUCCESS('✓ Database backup completed'))
            
            # Optionally backup media files
            if options['with_media']:
                self.stdout.write('\n[2/2] Backing up media files...')
                call_command('mediabackup', '--clean')
                self.stdout.write(self.style.SUCCESS('✓ Media backup completed'))
            else:
                self.stdout.write('\n[2/2] Media backup skipped (use --with-media to include)')
            
            # Show backup location
            backup_dir = getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups')
            
            # Count backup files
            db_backups = len([f for f in os.listdir(backup_dir) if f.endswith('.backup')]) if os.path.exists(backup_dir) else 0
            
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.SUCCESS('WEEKLY BACKUP COMPLETED SUCCESSFULLY'))
            self.stdout.write(f'Location: {backup_dir}')
            self.stdout.write(f'Database backups stored: {db_backups}')
            self.stdout.write(f'Retention policy: Last 10 backups')
            self.stdout.write('=' * 60)
            
        except Exception as e:
            self.stdout.write('\n' + '=' * 60)
            self.stdout.write(self.style.ERROR(f'✗ BACKUP FAILED: {str(e)}'))
            self.stdout.write('=' * 60)
            raise
