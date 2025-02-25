import os
import shutil
import stat

from django.conf import settings
from django.core.management import call_command
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


def get_backup_directory():
    return os.getenv('BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))


def ensure_permissions(directory):
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    os.chmod(directory, stat.S_IRWXU)


@method_decorator(csrf_exempt, name='dispatch')
class BackupDatabaseView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        db_path = settings.DATABASES['default'].get('NAME')
        if not db_path:
            return Response(
                {'error': 'Database path is not configured properly'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        backup_dir = get_backup_directory()
        backup_path = os.path.join(backup_dir, 'db_backup.sqlite3')

        if not os.path.exists(db_path):
            return Response(
                {'error': 'Database file does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            ensure_permissions(backup_dir)
            shutil.copy2(db_path, backup_path)
            return Response(
                {'message': f'Database backup created at {backup_path}'},
                status=status.HTTP_201_CREATED
            )
        except PermissionError as e:
            return Response(
                {'error': f'Permission error: {str(e)}'},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {'error': f'An error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class RestoreDBView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        backup_dir = get_backup_directory()
        backup_filename = 'db_backup.sqlite3'
        backup_path = os.path.join(backup_dir, backup_filename)

        if not os.path.exists(backup_path):
            return Response(
                {'status': 'error', 'message': 'Backup file does not exist.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            call_command('dbrestore', input=backup_path)
            return Response(
                {'status': 'success', 'message': 'Database restored successfully.'}
            )
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
