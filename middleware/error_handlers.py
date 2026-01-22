"""
Error Handlers for Flask Application

Provides centralized error handling including:
- 404 Not Found
- 500 Internal Server Error
- Generic exception handling

Author: AutoAssistGroup Development Team
"""

import logging
from flask import render_template, jsonify, request

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Register all error handlers with the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle bad request errors."""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
            }), 400
        return render_template('error.html', 
                              error_code=400, 
                              error_message='Bad Request'), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle unauthorized errors."""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Authentication required'
            }), 401
        return render_template('error.html', 
                              error_code=401, 
                              error_message='Unauthorized - Please log in'), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle forbidden errors."""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Forbidden',
                'message': 'Access denied'
            }), 403
        return render_template('error.html', 
                              error_code=403, 
                              error_message='Access Forbidden'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        return render_template('error.html', 
                              error_code=404, 
                              error_message='Page Not Found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        logger.error(f"Internal server error: {error}")
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        return render_template('error.html', 
                              error_code=500, 
                              error_message='Internal Server Error'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        
        # Don't expose internal errors in production
        if app.config.get('DEBUG'):
            error_message = str(e)
        else:
            error_message = 'An unexpected error occurred'
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Server Error',
                'message': error_message
            }), 500
        
        return render_template('error.html', 
                              error_code=500, 
                              error_message=error_message), 500


# Custom exception classes for better error handling
class TicketNotFoundError(Exception):
    """Raised when a ticket is not found."""
    pass


class MemberNotFoundError(Exception):
    """Raised when a member is not found."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks permission."""
    pass


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class DatabaseError(Exception):
    """Raised when a database operation fails."""
    pass
