# backup_restore_views.py
import os
import stat
from django.http import JsonResponse
from django.core.management import call_command
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


def ensure_permissions(directory):
    """Ensure the directory has the necessary permissions."""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # Set directory permissions to allow read, write, and execute for the owner
    os.chmod(directory, stat.S_IRWXU)  # S_IRWXU = 0o700 (read, write, execute for owner)


@method_decorator(csrf_exempt, name='dispatch')
class BackupDBView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        backup_path = request.data.get('backup_path')
        if not backup_path:
            return JsonResponse({'status': 'error', 'message': 'Backup path is required.'}, status=400)

        try:
            # Ensure the directory exists and is writable
            backup_dir = os.path.dirname(backup_path)
            print(f"Backup directory: {backup_dir}")  # Debugging
            os.makedirs(backup_dir, exist_ok=True)

            # Check if the directory is writable
            if not os.access(backup_dir, os.W_OK):
                return JsonResponse({'status': 'error', 'message': f'Directory is not writable: {backup_dir}'},
                                    status=403)

            # Remove the existing file if it exists
            if os.path.exists(backup_path):
                print(f"Removing existing file: {backup_path}")  # Debugging
                os.remove(backup_path)

            # Perform the backup
            print(f"Creating backup at: {backup_path}")  # Debugging
            call_command('dbbackup', output_path=backup_dir, output_filename=os.path.basename(backup_path))
            return JsonResponse({'status': 'success', 'message': 'Database backup created successfully.'})
        except PermissionError as e:
            print(f"Permission error: {e}")  # Debugging
            return JsonResponse({'status': 'error', 'message': f'Permission error: {str(e)}'}, status=403)
        except Exception as e:
            print(f"An error occurred: {e}")  # Debugging
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class RestoreDBView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        backup_path = request.data.get('backup_path')
        if not backup_path:
            return JsonResponse({'status': 'error', 'message': 'Backup path is required.'}, status=400)

        if not os.path.exists(backup_path):
            return JsonResponse({'status': 'error', 'message': 'Backup file does not exist.'}, status=400)

        try:
            # Perform the restore
            call_command('dbrestore', input=backup_path)
            return JsonResponse({'status': 'success', 'message': 'Database restored successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
