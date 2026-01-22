from flask import Flask, jsonify
import os

# Create minimal Flask app for testing
app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'success',
        'message': 'Minimal Flask app is working!',
        'environment': os.environ.get('FLASK_ENV', 'development'),
        'python_version': os.sys.version
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'test-flask-app'
    })

# Export for Vercel 