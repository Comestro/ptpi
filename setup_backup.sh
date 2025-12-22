#!/bin/bash

# Database Backup Setup Script for Linux/Mac
# This script sets up automated weekly database backups using cron

echo "=========================================="
echo "Database Backup Setup"
echo "=========================================="
echo ""

# Get the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3 || which python)
MANAGE_PY="$PROJECT_DIR/manage.py"

echo "Project Directory: $PROJECT_DIR"
echo "Python Path: $PYTHON_PATH"
echo ""

# Create backups directory
echo "[1/3] Creating backups directory..."
mkdir -p "$PROJECT_DIR/backups"
chmod 755 "$PROJECT_DIR/backups"
echo "✓ Backups directory created at: $PROJECT_DIR/backups"
echo ""

# Prepare cron job
echo "[2/3] Setting up weekly backup cron job..."
CRON_JOB="0 2 * * 0 cd $PROJECT_DIR && $PYTHON_PATH $MANAGE_PY weekly_backup >> $PROJECT_DIR/backups/backup.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -v "weekly_backup"; echo "$CRON_JOB") | crontab -

echo "✓ Cron job added: Weekly backup every Sunday at 2:00 AM"
echo ""

# Test backup
echo "[3/3] Testing backup command..."
cd "$PROJECT_DIR"
$PYTHON_PATH $MANAGE_PY backup_db

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  - Automated weekly backups: Every Sunday at 2:00 AM"
echo "  - Backup location: $PROJECT_DIR/backups"
echo "  - Retention: Last 10 backups"
echo "  - Log file: $PROJECT_DIR/backups/backup.log"
echo ""
echo "Manual Commands:"
echo "  - Create backup now:    python manage.py backup_db"
echo "  - Weekly backup:        python manage.py weekly_backup"
echo "  - Backup via API:       POST /api/admin/backup/"
echo "  - List backups via API: GET /api/admin/backup/"
echo ""
echo "To view cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo ""
