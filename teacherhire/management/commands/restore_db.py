# teacherhire/management/commands/restore_db.py
import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Restore the SQLite3 database from backup'

    def handle(self, *args, **kwargs):
        db_path = settings.DATABASES['default']['NAME']
        backup_path = os.path.join(settings.BASE_DIR, 'db_backup.sqlite3')

        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            self.stdout.write(self.style.SUCCESS(f'Database restored from {backup_path}'))
        else:
            self.stdout.write(self.style.ERROR('Backup file does not exist'))