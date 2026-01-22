#!/bin/bash

# AutoAssistGroup Support System - Restore Script
# Restores application from backup files

set -e

# Configuration
BACKUP_DIR="/opt/backups/autoassist"
APP_DIR="/opt/autoassist"
SERVICE_NAME="autoassist"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# List available backups
list_backups() {
    log "Available backups:"
    ls -la "${BACKUP_DIR}"/*_manifest.txt 2>/dev/null | while read -r line; do
        backup_file=$(basename "$line" _manifest.txt)
        backup_date=$(echo "$backup_file" | sed 's/autoassist_backup_//')
        echo "  - $backup_file (created: $backup_date)"
    done
}

# Select backup to restore
select_backup() {
    if [[ -z "$1" ]]; then
        list_backups
        echo
        read -p "Enter backup name to restore (without _manifest.txt): " BACKUP_NAME
    else
        BACKUP_NAME="$1"
    fi
    
    if [[ ! -f "${BACKUP_DIR}/${BACKUP_NAME}_manifest.txt" ]]; then
        error "Backup not found: ${BACKUP_NAME}"
    fi
    
    log "Selected backup: ${BACKUP_NAME}"
}

# Stop services
stop_services() {
    log "Stopping services..."
    
    systemctl stop ${SERVICE_NAME} || warning "Failed to stop ${SERVICE_NAME}"
    systemctl stop nginx || warning "Failed to stop nginx"
    
    log "Services stopped"
}

# Restore application files
restore_application() {
    log "Restoring application files..."
    
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_app.tar.gz" ]]; then
        # Backup current application
        if [[ -d "${APP_DIR}" ]]; then
            mv "${APP_DIR}" "${APP_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
        fi
        
        # Restore application
        tar -xzf "${BACKUP_DIR}/${BACKUP_NAME}_app.tar.gz" -C /
        
        # Set proper ownership
        chown -R www-data:www-data "${APP_DIR}"
        
        log "Application files restored"
    else
        error "Application backup file not found: ${BACKUP_NAME}_app.tar.gz"
    fi
}

# Restore configuration files
restore_config() {
    log "Restoring configuration files..."
    
    # Restore Nginx configuration
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_nginx.conf" ]]; then
        cp "${BACKUP_DIR}/${BACKUP_NAME}_nginx.conf" /etc/nginx/sites-available/autoassist
        log "Nginx configuration restored"
    fi
    
    # Restore systemd service
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_service.service" ]]; then
        cp "${BACKUP_DIR}/${BACKUP_NAME}_service.service" /etc/systemd/system/autoassist.service
        systemctl daemon-reload
        log "Systemd service restored"
    fi
    
    # Restore Gunicorn configuration
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_gunicorn.conf.py" ]]; then
        cp "${BACKUP_DIR}/${BACKUP_NAME}_gunicorn.conf.py" "${APP_DIR}/gunicorn.conf.py"
        log "Gunicorn configuration restored"
    fi
    
    # Restore environment file
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_env" ]]; then
        cp "${BACKUP_DIR}/${BACKUP_NAME}_env" "${APP_DIR}/.env"
        chown www-data:www-data "${APP_DIR}/.env"
        log "Environment file restored"
    fi
}

# Restore database
restore_database() {
    log "Restoring database..."
    
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_db.tar.gz" ]]; then
        # Extract database backup
        tar -xzf "${BACKUP_DIR}/${BACKUP_NAME}_db.tar.gz" -C "${BACKUP_DIR}"
        
        # Get MongoDB URI from environment
        MONGODB_URI=$(grep MONGODB_URI "${APP_DIR}/.env" 2>/dev/null | cut -d'=' -f2- || echo "")
        
        if [[ -n "${MONGODB_URI}" ]]; then
            # Restore database
            mongorestore --uri="${MONGODB_URI}" --drop "${BACKUP_DIR}/${BACKUP_NAME}_db"
            
            # Clean up extracted files
            rm -rf "${BACKUP_DIR}/${BACKUP_NAME}_db"
            
            log "Database restored"
        else
            warning "MongoDB URI not found in .env file, skipping database restore"
        fi
    else
        warning "Database backup not found, skipping database restore"
    fi
}

# Restore logs
restore_logs() {
    log "Restoring logs..."
    
    # Restore Nginx and Gunicorn logs
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_logs.tar.gz" ]]; then
        tar -xzf "${BACKUP_DIR}/${BACKUP_NAME}_logs.tar.gz" -C /
        log "System logs restored"
    fi
    
    # Restore application logs
    if [[ -f "${BACKUP_DIR}/${BACKUP_NAME}_app_logs.tar.gz" ]]; then
        tar -xzf "${BACKUP_DIR}/${BACKUP_NAME}_app_logs.tar.gz" -C "${APP_DIR}"
        chown -R www-data:www-data "${APP_DIR}/logs"
        log "Application logs restored"
    fi
}

# Recreate virtual environment
recreate_venv() {
    log "Recreating virtual environment..."
    
    # Remove existing virtual environment
    rm -rf "${APP_DIR}/venv"
    
    # Create new virtual environment
    sudo -u www-data python3.9 -m venv "${APP_DIR}/venv"
    
    # Install requirements
    sudo -u www-data "${APP_DIR}/venv/bin/pip" install --upgrade pip
    sudo -u www-data "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements-ec2.txt"
    
    log "Virtual environment recreated"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Test Nginx configuration
    nginx -t || error "Nginx configuration test failed"
    
    # Start services
    systemctl start nginx
    systemctl start ${SERVICE_NAME}
    
    # Check service status
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log "Application service started successfully"
    else
        error "Failed to start application service"
    fi
    
    if systemctl is-active --quiet nginx; then
        log "Nginx service started successfully"
    else
        error "Failed to start Nginx service"
    fi
}

# Verify restoration
verify_restoration() {
    log "Verifying restoration..."
    
    # Check if application is accessible
    sleep 5  # Wait for services to start
    
    if curl -f -s http://localhost/health > /dev/null; then
        log "Application health check passed"
    else
        warning "Application health check failed"
    fi
    
    # Check service status
    systemctl status ${SERVICE_NAME} --no-pager -l
    systemctl status nginx --no-pager -l
    
    log "Restoration verification completed"
}

# Display restoration summary
restoration_summary() {
    log "Restoration completed successfully!"
    echo
    info "=== RESTORATION SUMMARY ==="
    echo "Backup restored: ${BACKUP_NAME}"
    echo "Application directory: ${APP_DIR}"
    echo "Service name: ${SERVICE_NAME}"
    echo
    info "=== NEXT STEPS ==="
    echo "1. Verify application functionality:"
    echo "   curl http://your-domain.com/health"
    echo
    echo "2. Check service logs:"
    echo "   sudo journalctl -u ${SERVICE_NAME} -f"
    echo "   sudo tail -f /var/log/nginx/autoassist_access.log"
    echo
    echo "3. Test login functionality:"
    echo "   - Admin: admin001 / admin@123"
    echo "   - Tech Director: marc001 / tech@123"
    echo
    warning "Remember to:"
    echo "- Update DNS if domain changed"
    echo "- Verify SSL certificate if using HTTPS"
    echo "- Check MongoDB connection"
    echo "- Update any hardcoded URLs in configuration"
}

# Main restore function
main() {
    log "Starting AutoAssistGroup restoration process..."
    
    check_root
    select_backup "$1"
    stop_services
    restore_application
    restore_config
    restore_database
    restore_logs
    recreate_venv
    start_services
    verify_restoration
    restoration_summary
}

# Show usage if no arguments
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 [backup_name]"
    echo
    echo "Examples:"
    echo "  $0                                    # Interactive mode"
    echo "  $0 autoassist_backup_20240101_120000 # Restore specific backup"
    echo
    list_backups
    exit 0
fi

# Run main function
main "$@"
