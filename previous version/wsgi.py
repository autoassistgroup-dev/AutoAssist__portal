#!/usr/bin/env python3
"""
WSGI Entry Point for AutoAssistGroup Support System
Production deployment configuration for AWS EC2
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = 'False'

# Import the Flask application
from app import app

# Configure for production
app.config['DEBUG'] = False
app.config['TESTING'] = False

# This is the WSGI application object
application = app

if __name__ == "__main__":
    # For development testing only
    app.run(host='0.0.0.0', port=5000, debug=False)
