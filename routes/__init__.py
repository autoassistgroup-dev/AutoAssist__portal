"""
Routes Package

This package contains all Flask route blueprints organized by functionality.
Import and register blueprints in the main app factory.

Author: AutoAssistGroup Development Team
"""

# Import all blueprints
from routes.auth_routes import auth_bp
from routes.health_routes import health_bp
from routes.ticket_routes import ticket_bp
from routes.admin_routes import admin_bp
from routes.n8n_routes import n8n_bp
from routes.webhook_routes import webhook_bp
from routes.attachment_routes import attachment_bp
from routes.ai_routes import ai_bp
from routes.document_routes import document_bp
from routes.email_template_routes import email_template_bp
from routes.main_routes import main_bp


def register_blueprints(app):
    """
    Register all blueprints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Authentication routes
    app.register_blueprint(auth_bp)
    
    # Health check routes
    app.register_blueprint(health_bp)
    
    # Ticket API routes
    app.register_blueprint(ticket_bp)
    
    # Admin routes
    app.register_blueprint(admin_bp)
    
    # N8N integration routes
    app.register_blueprint(n8n_bp)
    
    # Webhook routes
    app.register_blueprint(webhook_bp)
    
    # Attachment routes
    app.register_blueprint(attachment_bp)
    
    # Common Document routes
    from routes.common_document_routes import common_docs_bp
    app.register_blueprint(common_docs_bp)
    
    # AI routes
    app.register_blueprint(ai_bp)
    
    # Document routes (Templates/Files)
    app.register_blueprint(document_bp)
    
    # Email Template routes
    app.register_blueprint(email_template_bp)
    
    # Main page routes (index, dashboard, ticket detail, etc.)
    app.register_blueprint(main_bp)
    


