#!/bin/bash

# AutoAssistGroup Support System - Backup Script
# Creates automated backups of application data and configuration

set -e

# Configuration
BACKUP_DIR="/opt/backups/autoassist"
APP_DIR="/opt/autoassist"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="autoassist_backup_${DATE}"
RETENTION_DAYS=30

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Create backup directory
create_backup_dir() {
    log "Creating backup directory..."
    mkdir -p "${BACKUP_DIR}"
}

# Backup application files
backup_application() {
    log "Backing up application files..."
    
    # Create application backup
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_app.tar.gz" \
        --exclude="${APP_DIR}/venv" \
        --exclude="${APP_DIR}/logs" \
        --exclude="${APP_DIR}/uploads" \
        --exclude="${APP_DIR}/__pycache__" \
        --exclude="${APP_DIR}/.git" \
        -C "$(dirname ${APP_DIR})" "$(basename ${APP_DIR})"
    
    log "Application backup created: ${BACKUP_NAME}_app.tar.gz"
}

# Backup configuration files
backup_config() {
    log "Backing up configuration files..."
    
    # Backup Nginx configuration
    cp /etc/nginx/sites-available/autoassist "${BACKUP_DIR}/${BACKUP_NAME}_nginx.conf"
    
    # Backup systemd service
    cp /etc/systemd/system/autoassist.service "${BACKUP_DIR}/${BACKUP_NAME}_service.service"
    
    # Backup Gunicorn configuration
    cp "${APP_DIR}/gunicorn.conf.py" "${BACKUP_DIR}/${BACKUP_NAME}_gunicorn.conf.py"
    
    # Backup environment file (if exists)
    if [[ -f "${APP_DIR}/.env" ]]; then
        cp "${APP_DIR}/.env" "${BACKUP_DIR}/${BACKUP_NAME}_env"
    fi
    
    log "Configuration backup completed"
}

# Backup database (MongoDB)
backup_database() {
    log "Backing up database..."
    
    # Check if MongoDB is accessible
    if command -v mongodump &> /dev/null; then
        # Get MongoDB URI from environment
        MONGODB_URI=$(grep MONGODB_URI "${APP_DIR}/.env" 2>/dev/null | cut -d'=' -f2- || echo "")
        
        if [[ -n "${MONGODB_URI}" ]]; then
            # Create database backup
            mongodump --uri="${MONGODB_URI}" --out="${BACKUP_DIR}/${BACKUP_NAME}_db"
            
            # Compress database backup
            tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_db.tar.gz" -C "${BACKUP_DIR}" "${BACKUP_NAME}_db"
            rm -rf "${BACKUP_DIR}/${BACKUP_NAME}_db"
            
            log "Database backup created: ${BACKUP_NAME}_db.tar.gz"
        else
            warning "MongoDB URI not found in .env file, skipping database backup"
        fi
    else
        warning "mongodump not available, skipping database backup"
    fi
}

# Backup logs
backup_logs() {
    log "Backing up logs..."
    
    # Create logs backup
    tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_logs.tar.gz" \
        -C /var/log nginx/autoassist_*.log gunicorn/autoassist_*.log 2>/dev/null || true
    
    # Backup application logs
    if [[ -d "${APP_DIR}/logs" ]]; then
        tar -czf "${BACKUP_DIR}/${BACKUP_NAME}_app_logs.tar.gz" \
            -C "${APP_DIR}" logs/
    fi
    
    log "Logs backup completed"
}

# Create backup manifest
create_manifest() {
    log "Creating backup manifest..."
    
    cat > "${BACKUP_DIR}/${BACKUP_NAME}_manifest.txt" << EOF
AutoAssistGroup Support System Backup Manifest
=============================================
Backup Date: $(date)
Backup Name: ${BACKUP_NAME}
Server: $(hostname)
Application Directory: ${APP_DIR}

Files Included:
- Application code: ${BACKUP_NAME}_app.tar.gz
- Configuration files: ${BACKUP_NAME}_nginx.conf, ${BACKUP_NAME}_service.service, ${BACKUP_NAME}_gunicorn.conf.py
- Environment file: ${BACKUP_NAME}_env (if exists)
- Database backup: ${BACKUP_NAME}_db.tar.gz (if MongoDB available)
- Logs: ${BACKUP_NAME}_logs.tar.gz, ${BACKUP_NAME}_app_logs.tar.gz

Restore Instructions:
1. Stop services: systemctl stop autoassist nginx
2. Restore application: tar -xzf ${BACKUP_NAME}_app.tar.gz -C /
3. Restore configuration: cp ${BACKUP_NAME}_*.conf /etc/nginx/sites-available/
4. Restore service: cp ${BACKUP_NAME}_service.service /etc/systemd/system/
5. Restore database: tar -xzf ${BACKUP_NAME}_db.tar.gz && mongorestore
6. Start services: systemctl start autoassist nginx

EOF
    
    log "Backup manifest created: ${BACKUP_NAME}_manifest.txt"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
    
    find "${BACKUP_DIR}" -name "autoassist_backup_*" -type f -mtime +${RETENTION_DAYS} -delete
    
    log "Old backups cleaned up"
}

# Upload to S3 (optional)
upload_to_s3() {
    if [[ -n "${S3_BUCKET}" ]] && command -v aws &> /dev/null; then
        log "Uploading backup to S3..."
        
        aws s3 sync "${BACKUP_DIR}" "s3://${S3_BUCKET}/autoassist-backups/" \
            --exclude "*" \
            --include "${BACKUP_NAME}_*"
        
        log "Backup uploaded to S3"
    else
        warning "S3 upload skipped (S3_BUCKET not set or AWS CLI not available)"
    fi
}

# Send notification (optional)
send_notification() {
    if [[ -n "${NOTIFICATION_EMAIL}" ]] && command -v mail &> /dev/null; then
        log "Sending backup notification..."
        
        echo "AutoAssistGroup backup completed successfully on $(date)" | \
            mail -s "Backup Completed - ${BACKUP_NAME}" "${NOTIFICATION_EMAIL}"
        
        log "Notification sent"
    fi
}

# Main backup function
main() {
    log "Starting AutoAssistGroup backup process..."
    
    create_backup_dir
    backup_application
    backup_config
    backup_database
    backup_logs
    create_manifest
    cleanup_old_backups
    upload_to_s3
    send_notification
    
    log "Backup process completed successfully!"
    log "Backup location: ${BACKUP_DIR}"
    
    # Display backup summary
    echo
    echo "=== BACKUP SUMMARY ==="
    ls -lh "${BACKUP_DIR}/${BACKUP_NAME}_*"
    echo
    echo "Total backup size: $(du -sh ${BACKUP_DIR}/${BACKUP_NAME}_* | awk '{sum+=$1} END {print sum}')"
}

# Run main function
main "$@"
