import os
import shutil
import stat
from django.core.management.base import BaseCommand
from django.conf import settings


def get_backup_directory():
    return os.getenv('BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))


def ensure_permissions(directory):
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    os.chmod(directory, stat.S_IRWXU)


class Command(BaseCommand):
    help = 'Backup the SQLite3 database'

    def handle(self, *args, **kwargs):
        db_path = settings.DATABASES['default']['NAME']
        backup_dir = get_backup_directory()
        backup_path = os.path.join(backup_dir, 'db_backup.sqlite3')

        if not os.path.exists(db_path):
            self.stdout.write(self.style.ERROR('Database file does not exist'))
            return

        try:
            ensure_permissions(backup_dir)
            shutil.copy2(db_path, backup_path)
            self.stdout.write(self.style.SUCCESS(f'Database backup created at {backup_path}'))
        except PermissionError as e:
            self.stdout.write(self.style.ERROR(f'Permission error: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
