# Gunicorn Configuration for AutoAssistGroup Support System
# AWS EC2 Production Deployment

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/var/log/gunicorn/autoassist_access.log"
errorlog = "/var/log/gunicorn/autoassist_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "autoassist_support"

# Server mechanics
daemon = False
pidfile = "/var/run/gunicorn/autoassist.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Environment variables
raw_env = [
    'FLASK_ENV=production',
    'FLASK_DEBUG=False',
]

# Preload app for better performance
preload_app = True

# Worker timeout for long-running requests
timeout = 120

# Graceful timeout
graceful_timeout = 30

# Forwarded allow ips (for nginx proxy)
forwarded_allow_ips = "127.0.0.1"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
