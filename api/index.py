import os
import sys

# Production serverless entry point
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set production environment
os.environ['FLASK_ENV'] = 'production'
    
# Import main application
from app import app

# Configure for production
app.config['DEBUG'] = False
app.config['TESTING'] = False

# This is the main export for Vercel 