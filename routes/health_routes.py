"""
Health Check and System Status Routes

Provides endpoints for:
- Health check for deployments
- System status monitoring
- Database connectivity checks

Author: AutoAssistGroup Development Team
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for debugging serverless deployment.
    Used by load balancers and monitoring systems.
    """
    try:
        # Basic health info
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'version': '2.0'
        }
        
        # Test database connection
        try:
            from database import get_db
            db = get_db()
            # Simple ping test
            db.client.admin.command('ping')
            health_data['database'] = 'connected'
        except Exception as db_error:
            health_data['database'] = f'error: {str(db_error)}'
            health_data['status'] = 'degraded'
        
        status_code = 200 if health_data['status'] == 'healthy' else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@health_bp.route('/api/status', methods=['GET'])
def api_status():
    """Get detailed API status information."""
    return jsonify({
        'success': True,
        'status': 'operational',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'tickets': 'operational',
            'auth': 'operational',
            'webhooks': 'operational'
        }
    })


@health_bp.route('/test', methods=['GET'])
def test_route():
    """Simple test route to verify server is running."""
    return jsonify({
        'success': True,
        'message': 'AutoAssistGroup Support System is running',
        'timestamp': datetime.now().isoformat()
    })
