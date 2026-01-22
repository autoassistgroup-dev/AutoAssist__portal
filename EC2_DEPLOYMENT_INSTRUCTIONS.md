# AutoAssistGroup EC2 Deployment Instructions

## 🚀 Quick Start Guide for Amazon Linux EC2

### Prerequisites
- ✅ AWS EC2 instance running Amazon Linux
- ✅ .pem file for SSH access
- ✅ Domain name (optional, can use EC2 public IP)

## Step 1: Upload to Git Repository

### Option A: Create New GitHub Repository
1. Go to [GitHub](https://github.com) and create a new repository
2. Name it: `autoassist-ec2-deployment`
3. Make it **Public** (so EC2 can clone without authentication)
4. Don't initialize with README (we already have files)

### Option B: Use Existing Repository
If you already have a Git repository, push these files to it.

### Upload Your Files
```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit files
git commit -m "Initial commit - AutoAssistGroup EC2 deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/autoassist-ec2-deployment.git

# Push to GitHub
git push -u origin main
```

## Step 2: Connect to Your EC2 Instance

### Set up SSH Key Permissions
```bash
# On your local machine, set correct permissions for .pem file
chmod 400 your-key-file.pem
```

### Connect to EC2
```bash
# Connect to your EC2 instance
ssh -i "your-key-file.pem" ec2-user@YOUR_EC2_PUBLIC_IP
```

## Step 3: Clone Repository on EC2

```bash
# Update system
sudo yum update -y

# Install git if not present
sudo yum install -y git

# Clone your repository
git clone https://github.com/YOUR_USERNAME/autoassist-ec2-deployment.git

# Navigate to the project directory
cd autoassist-ec2-deployment
```

## Step 4: Run Deployment Script

```bash
# Make the deployment script executable
chmod +x deploy-amazon-linux.sh

# Set your domain name (replace with your actual domain or EC2 public IP)
export DOMAIN_NAME="your-domain.com"
# OR use EC2 public IP:
# export DOMAIN_NAME="YOUR_EC2_PUBLIC_IP"

# Optional: Enable SSL setup (only if you have a domain)
# export SETUP_SSL="true"

# Run the deployment script as root
sudo ./deploy-amazon-linux.sh
```

## Step 5: Configure Environment Variables

```bash
# Copy environment template
sudo cp /opt/autoassist/env.template /opt/autoassist/.env

# Edit environment file
sudo nano /opt/autoassist/.env
```

### Required Environment Variables:
```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secure-secret-key-here

# MongoDB Configuration (REQUIRED)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/support_tickets

# Domain Configuration
DOMAIN_NAME=your-domain.com

# Security
SESSION_TIMEOUT=3600
RATE_LIMIT_ENABLED=True
```

## Step 6: Initialize Database

```bash
# Initialize the database
sudo -u ec2-user /opt/autoassist/venv/bin/python /opt/autoassist/init_database.py
```

## Step 7: Start Services

```bash
# Restart the application
sudo systemctl restart autoassist

# Check service status
sudo systemctl status autoassist
sudo systemctl status nginx

# View logs
sudo journalctl -u autoassist -f
```

## Step 8: Test Your Application

### Health Check
```bash
# Test health endpoint
curl http://YOUR_EC2_PUBLIC_IP/health
```

### Access Application
- **URL**: `http://YOUR_EC2_PUBLIC_IP` or `http://your-domain.com`
- **Admin Login**: admin001 / admin@123
- **Tech Director Login**: marc001 / tech@123

## 🔧 Troubleshooting

### Check Service Status
```bash
# Check if services are running
sudo systemctl status autoassist
sudo systemctl status nginx

# Check logs
sudo journalctl -u autoassist -n 50
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs for errors
sudo journalctl -u autoassist -f

# Test application manually
sudo -u ec2-user /opt/autoassist/venv/bin/python /opt/autoassist/wsgi.py
```

#### 2. Database Connection Issues
```bash
# Test MongoDB connection
sudo -u ec2-user /opt/autoassist/venv/bin/python -c "
from database import get_db
db = get_db()
print('Database connection successful')
"
```

#### 3. Permission Issues
```bash
# Fix ownership
sudo chown -R ec2-user:ec2-user /opt/autoassist
sudo chown -R ec2-user:ec2-user /var/log/gunicorn
sudo chown -R ec2-user:ec2-user /var/run/gunicorn
```

#### 4. Nginx Issues
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

## 🔒 Security Configuration

### Configure Firewall
```bash
# Check current firewall rules
sudo iptables -L

# If needed, configure firewall
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo service iptables save
```

### SSL Certificate (Optional)
If you have a domain name:
```bash
# Install Certbot
sudo yum install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

## 📊 Monitoring

### View Logs
```bash
# Application logs
sudo journalctl -u autoassist -f

# Nginx access logs
sudo tail -f /var/log/nginx/autoassist_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/autoassist_error.log
```

### Health Monitoring
```bash
# Check application health
curl http://YOUR_EC2_PUBLIC_IP/health

# Check system resources
top
df -h
free -h
```

## 🔄 Backup and Updates

### Backup Application
```bash
# Run backup script
sudo /opt/autoassist/backup.sh
```

### Update Application
```bash
# Pull latest changes from Git
cd /opt/autoassist
sudo -u ec2-user git pull origin main

# Restart services
sudo systemctl restart autoassist
```

## 📞 Support

### Default Login Credentials
- **Admin**: admin001 / admin@123
- **Technical Director**: marc001 / tech@123

### Useful Commands
```bash
# Quick health check
curl http://YOUR_EC2_PUBLIC_IP/health

# Check all services
sudo systemctl status autoassist nginx

# View real-time logs
sudo journalctl -u autoassist -f
```

---

## 🎉 Deployment Complete!

Your AutoAssistGroup Support System should now be running on AWS EC2!

**Next Steps:**
1. Configure your domain DNS to point to your EC2 public IP
2. Set up SSL certificate if using a domain
3. Test all functionality
4. Set up monitoring and backups

**Access your application at:** `http://YOUR_EC2_PUBLIC_IP`
