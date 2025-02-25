# teacherhire/management/commands/backup_db.py
import os
import shutil
import stat
from django.core.management.base import BaseCommand
from django.conf import settings


def ensure_permissions(directory):
    """Ensure the directory has the necessary permissions."""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # Set directory permissions to allow read, write, and execute for the owner
    os.chmod(directory, stat.S_IRWXU)  # S_IRWXU = 0o700 (read, write, execute for owner)


class Command(BaseCommand):
    help = 'Backup the SQLite3 database'

    def handle(self, *args, **kwargs):
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = os.getenv('BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
        backup_path = os.path.join(backup_dir, 'db_backup.sqlite3')

        if not os.path.exists(db_path):
            self.stdout.write(self.style.ERROR('Database file does not exist'))
            return

        try:
            # Ensure the backup directory has the necessary permissions
            ensure_permissions(backup_dir)

            # Perform the backup
            shutil.copy2(db_path, backup_path)
            self.stdout.write(self.style.SUCCESS(f'Database backup created at {backup_path}'))
        except PermissionError as e:
            self.stdout.write(self.style.ERROR(f'Permission error: {str(e)}'))
            self.stdout.write(self.style.ERROR(
                'Please ensure you have write permissions for the directory or run the script as an administrator.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
