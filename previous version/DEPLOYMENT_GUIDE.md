# AutoAssistGroup Support System - AWS EC2 Deployment Guide

This guide will help you deploy the AutoAssistGroup Support System on AWS EC2 with a production-ready setup using Nginx, Gunicorn, and systemd.

## 📋 Prerequisites

### AWS EC2 Instance Requirements
- **Instance Type**: t3.medium or larger (recommended: t3.large for production)
- **Operating System**: Ubuntu 20.04 LTS or 22.04 LTS
- **Storage**: Minimum 20GB EBS volume
- **Security Groups**: 
  - SSH (port 22) from your IP
  - HTTP (port 80) from anywhere
  - HTTPS (port 443) from anywhere (if using SSL)

### Domain and DNS
- A registered domain name
- DNS A record pointing to your EC2 instance's public IP

### External Services
- MongoDB Atlas account (or self-hosted MongoDB)
- Email service credentials (optional, for notifications)

## 🚀 Quick Deployment

### Step 1: Launch EC2 Instance
1. Launch an Ubuntu 20.04/22.04 LTS instance on AWS EC2
2. Configure security groups as mentioned above
3. Connect to your instance via SSH

### Step 2: Upload Application Code
```bash
# Clone or upload your application code to the instance
git clone <your-repository-url> /tmp/autoassist
cd /tmp/autoassist

# Or upload via SCP from your local machine
# scp -r . ec2-user@your-ec2-ip:/tmp/autoassist
```

### Step 3: Run Deployment Script
```bash
# Make the deployment script executable
chmod +x deploy.sh

# Set your domain name (replace with your actual domain)
export DOMAIN_NAME="your-domain.com"

# Optional: Enable SSL setup
export SETUP_SSL="true"

# Run the deployment script as root
sudo ./deploy.sh
```

## 🔧 Manual Deployment (Alternative)

If you prefer manual deployment or need to customize the setup:

### Step 1: System Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.9 python3.9-venv python3.9-dev nginx \
    build-essential libssl-dev libffi-dev git curl wget
```

### Step 2: Application Setup
```bash
# Create application directory
sudo mkdir -p /opt/autoassist
sudo chown www-data:www-data /opt/autoassist

# Copy application files
sudo cp -r . /opt/autoassist/
cd /opt/autoassist

# Create virtual environment
sudo -u www-data python3.9 -m venv venv
sudo -u www-data venv/bin/pip install -r requirements-ec2.txt
```

### Step 3: Configure Services
```bash
# Copy configuration files
sudo cp nginx.conf /etc/nginx/sites-available/autoassist
sudo cp autoassist.service /etc/systemd/system/
sudo cp gunicorn.conf.py /opt/autoassist/

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/autoassist /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Enable systemd service
sudo systemctl daemon-reload
sudo systemctl enable autoassist
```

### Step 4: Environment Configuration
```bash
# Create environment file
sudo cp .env.template .env
sudo nano .env
```

Configure the following variables in `.env`:
```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secure-secret-key-here

# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/support_tickets

# Domain Configuration
DOMAIN_NAME=your-domain.com

# Email Configuration (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Step 5: Initialize Database
```bash
# Initialize the database
sudo -u www-data /opt/autoassist/venv/bin/python init_database.py
```

### Step 6: Start Services
```bash
# Start services
sudo systemctl start autoassist
sudo systemctl start nginx

# Check status
sudo systemctl status autoassist
sudo systemctl status nginx
```

## 🔒 SSL Certificate Setup

### Using Let's Encrypt (Recommended)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Using AWS Certificate Manager
1. Request a certificate in AWS Certificate Manager
2. Validate domain ownership
3. Configure Application Load Balancer with SSL termination
4. Update Nginx configuration for HTTP only (ALB handles HTTPS)

## 📊 Monitoring and Maintenance

### Service Management
```bash
# Check service status
sudo systemctl status autoassist
sudo systemctl status nginx

# Restart services
sudo systemctl restart autoassist
sudo systemctl restart nginx

# View logs
sudo journalctl -u autoassist -f
sudo tail -f /var/log/nginx/autoassist_access.log
sudo tail -f /var/log/nginx/autoassist_error.log
```

### Application Logs
```bash
# Gunicorn logs
sudo tail -f /var/log/gunicorn/autoassist_access.log
sudo tail -f /var/log/gunicorn/autoassist_error.log

# Application logs
sudo tail -f /opt/autoassist/logs/app.log
```

### Database Maintenance
```bash
# Connect to MongoDB (if using local MongoDB)
mongosh

# Or connect to MongoDB Atlas
mongosh "mongodb+srv://username:password@cluster.mongodb.net/support_tickets"
```

## 🔧 Configuration Files

### Nginx Configuration
The `nginx.conf` file includes:
- Reverse proxy setup for Gunicorn
- Static file serving
- Rate limiting for security
- Security headers
- Gzip compression
- SSL configuration (commented out)

### Gunicorn Configuration
The `gunicorn.conf.py` file includes:
- Worker process configuration
- Logging setup
- Security settings
- Performance optimizations

### Systemd Service
The `autoassist.service` file includes:
- Service definition
- User/group settings
- Environment variables
- Security restrictions
- Auto-restart configuration

## 🚨 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check service status
sudo systemctl status autoassist

# Check logs
sudo journalctl -u autoassist -n 50

# Test configuration
sudo -u www-data /opt/autoassist/venv/bin/python wsgi.py
```

#### 2. Nginx Configuration Errors
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

#### 3. Database Connection Issues
```bash
# Test MongoDB connection
sudo -u www-data /opt/autoassist/venv/bin/python -c "
from database import get_db
db = get_db()
print('Database connection successful')
"
```

#### 4. Permission Issues
```bash
# Fix ownership
sudo chown -R www-data:www-data /opt/autoassist
sudo chown -R www-data:www-data /var/log/gunicorn
sudo chown -R www-data:www-data /var/run/gunicorn
```

### Performance Optimization

#### 1. Increase Worker Processes
Edit `gunicorn.conf.py`:
```python
workers = multiprocessing.cpu_count() * 2 + 1
```

#### 2. Enable Nginx Caching
Add to `nginx.conf`:
```nginx
location /static/ {
    alias /opt/autoassist/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

#### 3. Database Optimization
- Ensure proper indexing in MongoDB
- Monitor slow queries
- Consider connection pooling

## 🔐 Security Considerations

### 1. Firewall Configuration
```bash
# Configure UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
```

### 2. Regular Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
sudo -u www-data /opt/autoassist/venv/bin/pip install --upgrade -r requirements-ec2.txt
```

### 3. Backup Strategy
```bash
# Create backup script
sudo crontab -e
# Add: 0 2 * * * /opt/autoassist/backup.sh
```

### 4. Monitoring
- Set up CloudWatch monitoring for EC2
- Monitor application logs
- Set up alerts for service failures

## 📈 Scaling Considerations

### Horizontal Scaling
- Use Application Load Balancer
- Deploy multiple EC2 instances
- Use RDS for database (if migrating from MongoDB)

### Vertical Scaling
- Increase EC2 instance size
- Optimize Gunicorn worker configuration
- Implement caching (Redis)

### Database Scaling
- Use MongoDB Atlas with auto-scaling
- Implement read replicas
- Consider sharding for large datasets

## 🆘 Support

### Default Login Credentials
- **Admin**: admin001 / admin@123
- **Technical Director**: marc001 / tech@123

### Useful Commands
```bash
# Quick health check
curl http://your-domain.com/health

# Check all services
sudo systemctl status autoassist nginx

# View real-time logs
sudo journalctl -u autoassist -f
```

### Getting Help
1. Check application logs first
2. Verify configuration files
3. Test individual components
4. Check AWS CloudWatch logs
5. Review MongoDB Atlas logs (if using)

---

**Note**: This deployment guide assumes you have basic knowledge of Linux system administration and AWS EC2. For production deployments, consider additional security measures and monitoring solutions.
