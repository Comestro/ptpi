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

    def get_backup_dir(self):
        return getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups')

    def post(self, request):
        try:
            backup_dir = self.get_backup_dir()
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create timestamped backup using django-dbbackup
            # Note: django-dbbackup uses configured connectors to determine extension
            call_command('dbbackup', '--clean')
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Refresh list
            backups = self.get_backups_list(backup_dir)
            
            return Response(
                {
                    'status': 'success',
                    'message': 'Database backup created successfully',
                    'timestamp': timestamp,
                    'backup_location': str(backup_dir),
                    'recent_backups': [b['filename'] for b in backups[:5]],
                    'backups': backups,
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

    def get_backups_list(self, backup_dir):
        if not os.path.exists(backup_dir):
            return []
            
        extensions = ('.backup', '.sqlite3', '.psql', '.mysql', '.dump', '.gz', '.bin')
        backup_files = []
        
        for filename in os.listdir(backup_dir):
            if filename.endswith(extensions):
                filepath = os.path.join(backup_dir, filename)
                file_stat = os.stat(filepath)
                backup_files.append({
                    'filename': filename,
                    'size': f"{file_stat.st_size / (1024 * 1024):.2f} MB",
                    'created': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'mtime': file_stat.st_mtime
                })
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x['mtime'], reverse=True)
        return backup_files

    def get(self, request):
        """
        Get list of available backups
        """
        try:
            backup_dir = self.get_backup_dir()
            backup_files = self.get_backups_list(backup_dir)
            
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
    """
    API endpoint to restore a database from a specific backup file.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        filename = request.data.get('filename')
        
        if not filename:
            return Response(
                {'status': 'error', 'message': 'Backup filename is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        backup_dir = getattr(settings, 'BACKUP_DIR', settings.BASE_DIR / 'backups')
        backup_path = os.path.join(backup_dir, filename)

        if not os.path.exists(backup_path):
            # Fallback check if filename was passed without extension or with path issues
            return Response(
                {'status': 'error', 'message': f'Backup file "{filename}" does not exist at {backup_dir}'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Important: dbbackup uses connectors. 
            # dbrestore needs to know where the file is.
            # Using --input-filename and --noinput for non-interactive restore
            call_command('dbrestore', '--noinput', '--input-filename', filename)
            
            return Response(
                {'status': 'success', 'message': f'Database restored successfully from {filename}'}
            )
        except Exception as e:
            return Response(
                {'status': 'error', 'message': f'Restore failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
