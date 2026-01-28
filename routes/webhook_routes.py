"""
Webhook Routes

Handles webhook operations including:
- Tech Director referral webhooks
- Reply webhooks from external systems
- Webhook status and health monitoring
- Reminder scheduling

Author: AutoAssistGroup Development Team
"""

import os
import logging
import threading
import time
import requests
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from middleware.session_manager import is_authenticated, is_admin, safe_member_lookup
from config.settings import WEBHOOK_URL

logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('webhook', __name__, url_prefix='/api/webhook')

# In-memory storage for webhook status tracking
_webhook_status = {}
_webhook_lock = threading.Lock()


@webhook_bp.route('/tech-director/<ticket_id>', methods=['POST'])
def refer_to_tech_director(ticket_id):
    """
    Dedicated endpoint to refer ticket to Tech Director and trigger webhook.
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        from database import get_db
        db = get_db()
        
        # Get ticket
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Update ticket status
        db.update_ticket(ticket_id, {
            'status': 'Referred to Tech Director',
            'referred_at': datetime.now(),
            'referred_by': session.get('member_id')
        })
        
        # Trigger webhook asynchronously
        _trigger_tech_director_webhook_async(
            ticket_id, 
            ticket, 
            'referral',
            session.get('member_name')
        )
        
        logger.info(f"Ticket {ticket_id} referred to Tech Director by {session.get('member_name')}")
        
        return jsonify({
            'success': True,
            'message': 'Ticket referred to Technical Director',
            'ticket_id': ticket_id
        })
        
    except Exception as e:
        logger.error(f"Error referring ticket to tech director: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@webhook_bp.route('/status/<ticket_id>', methods=['GET'])
def get_webhook_status(ticket_id):
    """Get real-time status of async webhook for a ticket."""
    with _webhook_lock:
        status = _webhook_status.get(ticket_id, {
            'status': 'unknown',
            'message': 'No webhook data found'
        })
    
    return jsonify({
        'success': True,
        'ticket_id': ticket_id,
        'webhook': status
    })


@webhook_bp.route('/health', methods=['GET'])
def webhook_health():
    """Get overall health status of the webhook system."""
    return jsonify({
        'success': True,
        'status': 'operational',
        'webhook_url': WEBHOOK_URL[:50] + '...' if len(WEBHOOK_URL) > 50 else WEBHOOK_URL,
        'pending_webhooks': len(_webhook_status),
        'timestamp': datetime.now().isoformat()
    })


@webhook_bp.route('/cleanup', methods=['POST'])
def webhook_cleanup():
    """Clean up old webhook metadata (admin only)."""
    if not is_authenticated() or not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        with _webhook_lock:
            count = len(_webhook_status)
            _webhook_status.clear()
        
        logger.info(f"Webhook cleanup: cleared {count} entries")
        
        return jsonify({
            'success': True,
            'message': f'Cleared {count} webhook status entries'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@webhook_bp.route('/reply', methods=['POST'])
def webhook_reply():
    """
    Webhook endpoint for external systems (like n8n) to send ticket replies.
    No authentication required for webhook access.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
        
        ticket_id = data.get('ticket_id', data.get('ticketId'))
        if not ticket_id:
            return jsonify({'success': False, 'error': 'ticket_id required'}), 400
        
        message = data.get('message', data.get('response', data.get('reply', data.get('content', ''))))
        if not message:
            return jsonify({'success': False, 'error': 'message required'}), 400
        
        from database import get_db
        db = get_db()
        
        # Verify ticket exists
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Determine sender type - 'customer' for mail replies, 'webhook' for system
        customer_email = data.get('customer_email', data.get('from', ''))
        sender_type = 'customer' if customer_email else 'webhook'
        sender_name = data.get('sender_name', customer_email or 'External System')
        
        # Create reply
        reply_data = {
            'ticket_id': ticket_id,
            'message': message,
            'sender_name': sender_name,
            'sender_email': customer_email,
            'sender_type': sender_type,
            'attachments': data.get('attachments', []),
            'created_at': datetime.now()
        }
        
        reply_id = db.create_reply(reply_data)
        
        # Update ticket with unread reply flag
        db.update_ticket(ticket_id, {
            'has_unread_reply': True,
            'last_reply_at': datetime.now(),
            'status': 'Customer Replied' if sender_type == 'customer' else ticket.get('status')
        })
        
        logger.info(f"Webhook reply added to ticket {ticket_id}")
        
        return jsonify({
            'success': True,
            'message': 'Reply added successfully',
            'reply_id': str(reply_id),
            'ticket_id': ticket_id
        })
        
    except Exception as e:
        logger.error(f"Webhook reply error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@webhook_bp.route('/test', methods=['POST'])
def test_webhook():
    """Test the n8n webhook connection directly."""
    try:
        test_data = {
            'test': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'AutoAssistGroup webhook test'
        }
        
        response = requests.post(
            WEBHOOK_URL,
            json=test_data,
            timeout=10
        )
        
        return jsonify({
            'success': True,
            'webhook_status': response.status_code,
            'webhook_response': response.text[:500] if response.text else None
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Webhook timeout'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _trigger_tech_director_webhook_async(ticket_id, ticket_data, method, referred_by):
    """
    Asynchronous webhook trigger - runs in background thread.
    Does not block user interface.
    """
    def webhook_worker():
        max_retries = 3
        retry_delay = 2
        
        payload = {
            'ticket_id': ticket_id,
            'ticket_data': _serialize_for_webhook(ticket_data),
            'assignment_method': method,
            'referred_by': referred_by,
            'timestamp': datetime.now().isoformat()
        }
        
        with _webhook_lock:
            _webhook_status[ticket_id] = {
                'status': 'pending',
                'started_at': datetime.now().isoformat()
            }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    WEBHOOK_URL,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    with _webhook_lock:
                        _webhook_status[ticket_id] = {
                            'status': 'success',
                            'completed_at': datetime.now().isoformat()
                        }
                    logger.info(f"Webhook success for ticket {ticket_id}")
                    return
                    
            except Exception as e:
                logger.error(f"Webhook attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        with _webhook_lock:
            _webhook_status[ticket_id] = {
                'status': 'failed',
                'failed_at': datetime.now().isoformat()
            }
    
    thread = threading.Thread(target=webhook_worker, daemon=True)
    thread.start()


def _serialize_for_webhook(data):
    """Serialize data for webhook payload."""
    if not data:
        return None
    
    result = {}
    for key, value in data.items():
        if key == '_id':
            result['_id'] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = _serialize_for_webhook(value)
        elif isinstance(value, list):
            result[key] = [_serialize_for_webhook(v) if isinstance(v, dict) else str(v) if hasattr(v, '__str__') and not isinstance(v, (str, int, float, bool)) else v for v in value]
        else:
            result[key] = value
    
    return result
