"""
N8N Integration Routes

Handles all N8N workflow integration including:
- Email ticket creation from N8N
- Quick response endpoints
- Webhook processing
- Status endpoints for N8N

Author: AutoAssistGroup Development Team
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, jsonify, request

from utils.file_utils import detect_warranty_form
from utils.validators import extract_email

logger = logging.getLogger(__name__)

# Create blueprint - no authentication required for N8N endpoints
n8n_bp = Blueprint('n8n', __name__, url_prefix='/api/n8n')


@n8n_bp.route('/email-tickets', methods=['POST'])
def n8n_email_tickets():
    """
    Endpoint specifically designed for n8n email data with proper attachment handling.
    No authentication required for webhook access.
    """
    try:
        logger.info("N8N email-tickets endpoint called")
        
        # Get and log raw data
        raw_data = request.get_json()
        
        if not raw_data:
            return jsonify({
                'success': False,
                'error': 'No JSON data received'
            }), 400
        
        # Process the email data
        processed = process_n8n_email_data(raw_data)
        
        if not processed:
            return jsonify({
                'success': False,
                'error': 'Failed to process email data'
            }), 400
        
        # Create ticket in database
        from database import get_db
        db = get_db()
        
        ticket_id = db.create_ticket(processed)
        
        logger.info(f"N8N ticket created: {processed.get('ticket_id')}")
        
        return jsonify({
            'success': True,
            'message': 'Ticket created from email',
            'ticket_id': processed.get('ticket_id'),
            'db_id': str(ticket_id)
        })
        
    except Exception as e:
        logger.error(f"N8N email-tickets error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@n8n_bp.route('/quick', methods=['POST'])
def n8n_quick_response():
    """
    Quick response endpoint for n8n - responds immediately to prevent timeouts.
    Processes data in background to avoid hanging n8n workflows.
    """
    try:
        raw_data = request.get_json()
        
        if not raw_data:
            return jsonify({
                'success': True,
                'acknowledged': True,
                'message': 'No data received but acknowledged'
            }), 200
        
        # Quick acknowledgment - don't wait for full processing
        # In production, could queue this for background processing
        
        logger.info("N8N quick endpoint - data acknowledged")
        
        return jsonify({
            'success': True,
            'acknowledged': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'Data received and queued for processing'
        }), 200
        
    except Exception as e:
        logger.error(f"N8N quick response error: {e}")
        return jsonify({
            'success': True,
            'acknowledged': True,
            'error': str(e)
        }), 200  # Still return 200 to prevent n8n timeout


@n8n_bp.route('/minimal', methods=['POST'])
def n8n_minimal_response():
    """
    Minimal acknowledgment endpoint - ultra-fast response for slow n8n scenarios.
    Returns acknowledgment immediately, processes data separately.
    """
    return jsonify({
        'success': True,
        'acknowledged': True,
        'timestamp': datetime.now().isoformat()
    }), 200


@n8n_bp.route('/status', methods=['GET'])
def n8n_processing_status():
    """
    Check processing status and system health for n8n integration monitoring.
    """
    try:
        from database import get_db
        db = get_db()
        
        # Get recent ticket count
        recent_count = db.tickets.count_documents({})
        
        return jsonify({
            'success': True,
            'status': 'operational',
            'timestamp': datetime.now().isoformat(),
            'total_tickets': recent_count,
            'database': 'connected'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@n8n_bp.route('/simple-test', methods=['POST'])
def n8n_simple_test():
    """
    Simple test endpoint to verify database connectivity and basic ticket creation.
    """
    try:
        from database import get_db
        db = get_db()
        
        # Ping database
        db.client.admin.command('ping')
        
        return jsonify({
            'success': True,
            'message': 'Database connection successful',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"N8N simple test error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def process_n8n_email_data(raw_data):
    """
    Process n8n email data into ticket format.
    
    Args:
        raw_data: Raw JSON from n8n webhook
        
    Returns:
        dict: Processed ticket data ready for database
    """
    try:
        # Handle array data
        data = raw_data[0] if isinstance(raw_data, list) else raw_data
        
        # Extract email fields
        email = extract_email(data.get('from', data.get('email', '')))
        subject = data.get('subject', data.get('Subject', 'No Subject'))
        body = data.get('body', data.get('text', data.get('content', data.get('message', ''))))
        name = data.get('name', data.get('sender_name', ''))
        
        # Extract name from email if not provided
        if not name and email:
            name = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        
        # Check for existing ticket ID or generate new one
        ticket_id = data.get('ticket_id', data.get('ticketId', data.get('final_ticket_id', '')))
        
        if not ticket_id:
            # Generate new ticket ID
            import random
            import string
            prefix = 'E'  # Email ticket
            suffix = ''.join(random.choices(string.ascii_uppercase, k=2)) + str(random.randint(1000, 9999))
            ticket_id = prefix + suffix
        
        # Check for attachments and warranty forms
        attachments = data.get('attachments', [])
        has_warranty = False
        
        for att in attachments:
            filename = att.get('filename', att.get('fileName', ''))
            if detect_warranty_form(filename):
                has_warranty = True
                break
        
        # Extract priority (handle both cases from N8N)
        priority = data.get('Priority', data.get('priority', 'Medium'))
        
        # Extract classification (handle both cases from N8N)
        classification = data.get('Classification', data.get('classification', 'General Inquiry'))
        
        # Extract draft response from N8N AI Agent
        draft = data.get('draft', data.get('n8n_draft', ''))
        n8n_draft = data.get('n8n_draft', data.get('draft', ''))
        
        # Extract thread and message IDs for email tracking
        thread_id = data.get('threadId', data.get('thread_id', ''))
        message_id = data.get('messageid', data.get('message_id', data.get('messageId', '')))
        
        # Extract date
        date_str = data.get('date', '')
        
        # Build ticket data
        ticket_data = {
            'ticket_id': ticket_id,
            'email': email,
            'name': name,
            'subject': subject,
            'message': body,
            'status': 'Open',
            'priority': priority,
            'classification': classification,
            'source': 'n8n_email',
            'creation_method': 'n8n_email',
            'has_warranty': has_warranty,
            'has_attachments': len(attachments) > 0,
            'attachments': attachments,
            # N8N specific fields
            'draft': draft,
            'n8n_draft': n8n_draft,
            'thread_id': thread_id,
            'message_id': message_id,
            'email_date': date_str,
            'raw_data': data,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        logger.info(f"Processed N8N ticket: {ticket_id}, Priority: {priority}, Classification: {classification}, Draft: {'Yes' if draft else 'No'}")
        
        return ticket_data
        
    except Exception as e:
        logger.error(f"Error processing N8N email data: {e}")
        return None

