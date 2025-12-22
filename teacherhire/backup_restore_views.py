import os
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(csrf_exempt, name='dispatch')
class BackupDatabaseView(APIView):
    """
    API endpoint to create a database backup on-demand.
    Only accessible to admin users.
    Creates timestamped backups and automatically cleans up old ones.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            # Get backup directory
            backup_dir = getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups')
            
            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create timestamped backup using django-dbbackup
            call_command('dbbackup', '--clean')
            
            # Get current timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # List backup files to confirm
            backup_files = []
            if os.path.exists(backup_dir):
                backup_files = sorted(
                    [f for f in os.listdir(backup_dir) if f.endswith('.backup')],
                    reverse=True
                )[:5]  # Show latest 5 backups
            
            return Response(
                {
                    'status': 'success',
                    'message': 'Database backup created successfully',
                    'timestamp': timestamp,
                    'backup_location': str(backup_dir),
                    'recent_backups': backup_files,
                    'retention_policy': 'Last 10 backups are kept'
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': f'Backup failed: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """
        Get list of available backups
        """
        try:
            backup_dir = getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups')
            
            if not os.path.exists(backup_dir):
                return Response(
                    {
                        'status': 'success',
                        'backups': [],
                        'message': 'No backups found'
                    }
                )
            
            # List all backup files with details
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith('.backup'):
                    filepath = os.path.join(backup_dir, filename)
                    file_stat = os.stat(filepath)
                    backup_files.append({
                        'filename': filename,
                        'size': f"{file_stat.st_size / (1024 * 1024):.2f} MB",
                        'created': datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # Sort by creation time (newest first)
            backup_files.sort(key=lambda x: x['created'], reverse=True)
            
            return Response(
                {
                    'status': 'success',
                    'backup_location': str(backup_dir),
                    'total_backups': len(backup_files),
                    'backups': backup_files
                }
            )
            
        except Exception as e:
            return Response(
                {
                    'status': 'error',
                    'message': str(e)
                },
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
