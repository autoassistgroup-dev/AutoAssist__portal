#!/bin/bash

# AutoAssistGroup Support System - AWS EC2 Amazon Linux Deployment Script
# This script automates the deployment process on Amazon Linux EC2 instances

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="autoassist"
APP_DIR="/opt/autoassist"
APP_USER="ec2-user"
APP_GROUP="ec2-user"
DOMAIN_NAME="${DOMAIN_NAME:-your-domain.com}"  # Set this environment variable
PYTHON_VERSION="3.9"

# Logging function
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

# Update system packages
update_system() {
    log "Updating system packages..."
    yum update -y
    yum install -y curl wget git unzip
}

# Install Python and dependencies
install_python() {
    log "Installing Python ${PYTHON_VERSION} and dependencies..."
    
    # Install Python 3.9 and development tools
    yum install -y python39 python39-devel python39-pip \
                   gcc gcc-c++ make openssl-devel libffi-devel \
                   libxml2-devel libxslt-devel zlib-devel \
                   libjpeg-devel libpng-devel
}

# Install Nginx
install_nginx() {
    log "Installing Nginx..."
    
    # Install EPEL repository
    yum install -y epel-release
    
    # Install Nginx
    yum install -y nginx
    
    # Start and enable Nginx
    systemctl start nginx
    systemctl enable nginx
}

# Install MongoDB tools (optional, for local MongoDB)
install_mongodb_tools() {
    log "Installing MongoDB tools..."
    
    # Create MongoDB repository file
    cat > /etc/yum.repos.d/mongodb-org-6.0.repo << EOF
[mongodb-org-6.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2/mongodb-org/6.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-6.0.asc
EOF
    
    yum install -y mongodb-mongosh
}

# Create application directory and user
setup_app_directory() {
    log "Setting up application directory and user..."
    
    # Create application directory
    mkdir -p ${APP_DIR}
    mkdir -p /var/log/gunicorn
    mkdir -p /var/run/gunicorn
    
    # Set ownership (ec2-user is the default user on Amazon Linux)
    chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}
    chown -R ${APP_USER}:${APP_GROUP} /var/log/gunicorn
    chown -R ${APP_USER}:${APP_GROUP} /var/run/gunicorn
}

# Create Python virtual environment
setup_python_venv() {
    log "Creating Python virtual environment..."
    
    # Create virtual environment
    python3.9 -m venv ${APP_DIR}/venv
    
    # Activate virtual environment and upgrade pip
    source ${APP_DIR}/venv/bin/activate
    pip install --upgrade pip setuptools wheel
    
    # Install requirements
    if [[ -f "requirements-ec2.txt" ]]; then
        pip install -r requirements-ec2.txt
    else
        error "requirements-ec2.txt not found!"
    fi
}

# Deploy application code
deploy_application() {
    log "Deploying application code..."
    
    # Copy application files
    cp -r . ${APP_DIR}/
    
    # Remove unnecessary files
    rm -f ${APP_DIR}/vercel.json ${APP_DIR}/vercel-test.json
    
    # Set proper permissions
    chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}
    chmod +x ${APP_DIR}/wsgi.py
    
    # Create necessary directories
    mkdir -p ${APP_DIR}/logs
    mkdir -p ${APP_DIR}/uploads
    chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}/logs ${APP_DIR}/uploads
}

# Configure Nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # Copy Nginx configuration
    cp nginx.conf /etc/nginx/conf.d/${APP_NAME}.conf
    
    # Replace domain name in configuration
    sed -i "s/your-domain.com/${DOMAIN_NAME}/g" /etc/nginx/conf.d/${APP_NAME}.conf
    
    # Remove default server block
    rm -f /etc/nginx/conf.d/default.conf
    
    # Test Nginx configuration
    nginx -t || error "Nginx configuration test failed"
    
    # Reload Nginx
    systemctl reload nginx
}

# Configure systemd service
configure_systemd() {
    log "Configuring systemd service..."
    
    # Copy systemd service file
    cp autoassist.service /etc/systemd/system/
    
    # Update service file for Amazon Linux (ec2-user instead of www-data)
    sed -i 's/User=www-data/User=ec2-user/g' /etc/systemd/system/autoassist.service
    sed -i 's/Group=www-data/Group=ec2-user/g' /etc/systemd/system/autoassist.service
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable ${APP_NAME}
}

# Setup SSL with Let's Encrypt (optional)
setup_ssl() {
    if [[ "${SETUP_SSL}" == "true" ]]; then
        log "Setting up SSL with Let's Encrypt..."
        
        # Install Certbot
        yum install -y certbot python3-certbot-nginx
        
        # Get SSL certificate
        certbot --nginx -d ${DOMAIN_NAME} -d www.${DOMAIN_NAME} --non-interactive --agree-tos --email admin@${DOMAIN_NAME}
        
        # Setup auto-renewal
        systemctl enable certbot.timer
        systemctl start certbot.timer
    else
        warning "SSL setup skipped. Set SETUP_SSL=true to enable SSL."
    fi
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    # Configure iptables (Amazon Linux uses iptables by default)
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -A INPUT -j DROP
    
    # Save iptables rules
    service iptables save
}

# Create environment file template
create_env_template() {
    log "Creating environment file template..."
    
    cat > ${APP_DIR}/env.template << EOF
# AutoAssistGroup Support System - Environment Configuration
# Copy this file to .env and fill in your values

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here

# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/support_tickets

# Email Configuration (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Domain Configuration
DOMAIN_NAME=${DOMAIN_NAME}

# Security
SESSION_TIMEOUT=3600
RATE_LIMIT_ENABLED=True
EOF

    chown ${APP_USER}:${APP_GROUP} ${APP_DIR}/env.template
}

# Start services
start_services() {
    log "Starting services..."
    
    # Start the application
    systemctl start ${APP_NAME}
    
    # Check service status
    if systemctl is-active --quiet ${APP_NAME}; then
        log "Application service started successfully"
    else
        error "Failed to start application service"
    fi
    
    # Check Nginx status
    if systemctl is-active --quiet nginx; then
        log "Nginx service is running"
    else
        error "Nginx service is not running"
    fi
}

# Display deployment summary
deployment_summary() {
    log "Deployment completed successfully!"
    echo
    info "=== DEPLOYMENT SUMMARY ==="
    echo "Application Directory: ${APP_DIR}"
    echo "Domain Name: ${DOMAIN_NAME}"
    echo "Service Name: ${APP_NAME}"
    echo "User: ${APP_USER}"
    echo
    info "=== NEXT STEPS ==="
    echo "1. Copy env.template to .env and configure your environment variables:"
    echo "   sudo cp ${APP_DIR}/env.template ${APP_DIR}/.env"
    echo "   sudo nano ${APP_DIR}/.env"
    echo
    echo "2. Initialize the database:"
    echo "   sudo -u ${APP_USER} ${APP_DIR}/venv/bin/python ${APP_DIR}/init_database.py"
    echo
    echo "3. Restart the application:"
    echo "   sudo systemctl restart ${APP_NAME}"
    echo
    echo "4. Check service status:"
    echo "   sudo systemctl status ${APP_NAME}"
    echo "   sudo systemctl status nginx"
    echo
    echo "5. View logs:"
    echo "   sudo journalctl -u ${APP_NAME} -f"
    echo "   sudo tail -f /var/log/nginx/autoassist_access.log"
    echo
    info "=== ACCESS INFORMATION ==="
    echo "Application URL: http://${DOMAIN_NAME}"
    echo "Admin Login: admin001 / admin@123"
    echo "Tech Director Login: marc001 / tech@123"
    echo
    warning "Remember to:"
    echo "- Configure your domain DNS to point to this server"
    echo "- Set up SSL certificate if needed"
    echo "- Configure your MongoDB connection string"
    echo "- Update the SECRET_KEY in .env file"
}

# Main deployment function
main() {
    log "Starting AutoAssistGroup Support System deployment on Amazon Linux..."
    
    check_root
    update_system
    install_python
    install_nginx
    install_mongodb_tools
    setup_app_directory
    setup_python_venv
    deploy_application
    configure_nginx
    configure_systemd
    setup_ssl
    configure_firewall
    create_env_template
    start_services
    deployment_summary
}

# Run main function
main "$@"
