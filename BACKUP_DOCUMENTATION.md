# Database Backup System Documentation

## Overview
This project includes a comprehensive database backup system with:
- **Automated weekly backups** (scheduled via cron/Task Scheduler)
- **On-demand backups** via API endpoint
- **Automatic cleanup** of old backups (keeps last 10)
- **Timestamped backup files** for easy identification

## Quick Start

### 1. Setup (Linux/Mac)
```bash
chmod +x setup_backup.sh
./setup_backup.sh
```

### 2. Setup (Windows)
1. Create a folder: `C:\ptpi\backups`
2. Open Task Scheduler
3. Create Basic Task:
   - Name: "PTPI Weekly Backup"
   - Trigger: Weekly, Sunday, 2:00 AM
   - Action: Start a program
   - Program: `C:\path\to\python.exe`
   - Arguments: `C:\path\to\manage.py weekly_backup`
   - Start in: `C:\path\to\ptpi`

## Features

### 1. Manual Backup (Command Line)
```bash
# Create a backup now
python manage.py backup_db

# Weekly backup (same as automated)
python manage.py weekly_backup

# Backup with media files
python manage.py weekly_backup --with-media
```

### 2. API Endpoints

#### Create Backup (On-Demand)
**POST** `/api/admin/backup/`

**Authentication:** Admin user required

**Request:**
```bash
curl -X POST http://localhost:8000/api/admin/backup/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN"
```

**Response:**
```json
{
  "status": "success",
  "message": "Database backup created successfully",
  "timestamp": "2025-12-21 14:30:45",
  "backup_location": "/Users/comestro/ptpi/backups",
  "recent_backups": [
    "default-2025-12-21-143045.backup",
    "default-2025-12-14-020000.backup",
    "default-2025-12-07-020000.backup"
  ],
  "retention_policy": "Last 10 backups are kept"
}
```

#### List Backups
**GET** `/api/admin/backup/`

**Authentication:** Admin user required

**Response:**
```json
{
  "status": "success",
  "backup_location": "/Users/comestro/ptpi/backups",
  "total_backups": 5,
  "backups": [
    {
      "filename": "default-2025-12-21-143045.backup",
      "size": "15.32 MB",
      "created": "2025-12-21 14:30:45"
    },
    {
      "filename": "default-2025-12-14-020000.backup",
      "size": "14.87 MB",
      "created": "2025-12-14 02:00:00"
    }
  ]
}
```

## Configuration

### settings.py
```python
# Backup directory
BACKUP_DIR = BASE_DIR / 'backups'

# Django-dbbackup settings
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': BACKUP_DIR}
DBBACKUP_CLEANUP_KEEP = 10  # Keep last 10 backups
DBBACKUP_DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
```

### Cron Schedule (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add this line for weekly backup (Sunday 2:00 AM)
0 2 * * 0 cd /path/to/ptpi && python manage.py weekly_backup >> /path/to/ptpi/backups/backup.log 2>&1
```

### Other Schedules
```bash
# Daily at 2:00 AM
0 2 * * * cd /path/to/ptpi && python manage.py weekly_backup

# Every 6 hours
0 */6 * * * cd /path/to/ptpi && python manage.py weekly_backup

# Monday to Friday at 11:00 PM
0 23 * * 1-5 cd /path/to/ptpi && python manage.py weekly_backup
```

## Backup Files

### Naming Convention
```
default-YYYY-MM-DD-HHMMSS.backup
```

Example:
```
default-2025-12-21-143045.backup
```

### Location
```
/Users/comestro/ptpi/backups/
```

### Retention Policy
- **Automatic cleanup:** Old backups are automatically deleted
- **Kept:** Last 10 backups
- **Deleted:** Older backups beyond the 10 most recent

## Restore Database

### From Backup File
```bash
# Restore from specific backup
python manage.py dbrestore --input=/path/to/backup.backup

# Interactive restore (choose from available backups)
python manage.py dbrestore
```

### Via API
**POST** `/api/admin/restore/`

**Authentication:** Admin user required

## Monitoring

### View Backup Logs
```bash
# View last 50 lines of backup log
tail -n 50 backups/backup.log

# Follow backup log in real-time
tail -f backups/backup.log
```

### Check Backup Status
```bash
# List all backups with details
ls -lh backups/*.backup

# Count backups
ls backups/*.backup | wc -l
```

## Troubleshooting

### Issue: Backup fails with permission error
**Solution:**
```bash
chmod 755 backups
chmod 644 backups/*.backup
```

### Issue: Cron job not running
**Solution:**
```bash
# Check cron service is running
sudo service cron status  # Linux
# or
launchctl list | grep cron  # Mac

# Check cron logs
grep CRON /var/log/syslog  # Linux
```

### Issue: Backup directory full
**Solution:**
- Reduce `DBBACKUP_CLEANUP_KEEP` in settings.py
- Manually delete old backups
- Move backups to external storage

## Best Practices

1. **Regular Testing:** Test restore process monthly
2. **Off-site Backups:** Copy backups to external storage/cloud
3. **Monitor Logs:** Check backup.log regularly
4. **Disk Space:** Ensure sufficient disk space for backups
5. **Security:** Restrict backup directory permissions

## Advanced Configuration

### Backup to AWS S3
```python
# settings.py
DBBACKUP_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DBBACKUP_STORAGE_OPTIONS = {
    'access_key': 'YOUR_ACCESS_KEY',
    'secret_key': 'YOUR_SECRET_KEY',
    'bucket_name': 'your-backup-bucket',
}
```

### Email Notifications
Add to `weekly_backup.py`:
```python
from django.core.mail import send_mail

send_mail(
    'Backup Success',
    f'Weekly backup completed at {timestamp}',
    'admin@ptpi.com',
    ['notifications@ptpi.com'],
)
```

## Support

For issues or questions:
- Check logs: `backups/backup.log`
- Test manual backup: `python manage.py backup_db`
- Verify cron: `crontab -l`
