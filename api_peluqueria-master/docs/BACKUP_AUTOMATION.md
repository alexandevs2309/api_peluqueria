# Cron Configuration for Automated Backups

## Setup Instructions

### 1. Install cron job
```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily backup at 2:00 AM
0 2 * * * /path/to/scripts/backup-production.sh >> /var/log/backup.log 2>&1

# Weekly full backup at 3:00 AM on Sundays
0 3 * * 0 RETENTION_DAYS=90 /path/to/scripts/backup-production.sh >> /var/log/backup-weekly.log 2>&1

# Monthly backup with S3 upload at 4:00 AM on 1st of month
0 4 1 * * S3_BUCKET=my-backup-bucket /path/to/scripts/backup-production.sh >> /var/log/backup-monthly.log 2>&1
```

### 2. Environment Variables
```bash
# Create /etc/environment or ~/.bashrc
export BACKUP_DIR="/var/backups/peluqueria"
export RETENTION_DAYS="30"
export S3_BUCKET="my-backup-bucket"
export SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
export DB_USER="postgres"
export DB_NAME="barbershop_db"
```

### 3. Permissions
```bash
# Make script executable
chmod +x /path/to/scripts/backup-production.sh

# Create backup directory
sudo mkdir -p /var/backups/peluqueria
sudo chown $(whoami):$(whoami) /var/backups/peluqueria
```

### 4. Log Rotation
```bash
# Create /etc/logrotate.d/backup-logs
/var/log/backup*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
```

## Backup Schedule

| Frequency | Time | Retention | Location |
|-----------|------|-----------|----------|
| Daily | 2:00 AM | 30 days | Local |
| Weekly | 3:00 AM Sun | 90 days | Local + S3 |
| Monthly | 4:00 AM 1st | 1 year | S3 only |

## Monitoring Backups

### Check backup status
```bash
# View recent backups
ls -la /var/backups/peluqueria/

# Check backup logs
tail -f /var/log/backup.log

# Verify backup integrity
./scripts/verify-backup.sh backup_20241215_020000
```

### Slack Notifications
- ✅ Success notifications
- ❌ Failure alerts
- 📊 Weekly backup reports

## Restore Procedures

### Database Restore
```bash
# Stop application
docker-compose down

# Restore database
gunzip -c /var/backups/peluqueria/db_backup_TIMESTAMP.sql.gz | \
docker-compose exec -T db psql -U postgres -d barbershop_db

# Start application
docker-compose up -d
```

### Full System Restore
```bash
# Use the restore script
./scripts/restore.sh /var/backups/peluqueria/backup_TIMESTAMP
```