"""
AI Routes Blueprint

This module contains API endpoints for AI-related functionality,
including AI response generation and display.

Author: AutoAssistGroup Development Team
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')


@ai_bp.route('/display-response', methods=['POST', 'GET'])
def display_response():
    """
    Display or verify AI response generation.
    
    GET: Test endpoint availability
    POST: Process and save AI response data to ticket
    """
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'message': 'AI Display API is working',
            'timestamp': datetime.now().isoformat()
        })
    
    try:
        data = request.get_json() or {}
        
        ticket_id = data.get('ticket_id', '')
        ai_response = data.get('ai_response', data.get('draft', ''))
        
        if ticket_id and ai_response:
            # Save the AI draft to the ticket in database
            from database import get_db
            db = get_db()
            
            # First, try to find the ticket by ticket_id
            ticket = db.get_ticket_by_id(ticket_id)
            
            # If ticket not found, try to find by customer email (for reply scenarios)
            customer_email = data.get('from', data.get('customer_email', ''))
            if not ticket and customer_email:
                # Find the most recent ticket from this customer
                tickets = list(db.tickets.find(
                    {"email": customer_email}
                ).sort("created_at", -1).limit(1))
                if tickets:
                    ticket = tickets[0]
                    ticket_id = ticket.get('ticket_id')
                    logger.info(f"Found ticket {ticket_id} by customer email {customer_email}")
            
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found, creating update anyway")
            
            # Check if there's also a customer message to save as a reply
            customer_message = data.get('customer_message', data.get('body', data.get('message', '')))
            
            # If customer message provided, save it as a reply first
            if customer_message and customer_email and ticket:
                reply_data = {
                    'ticket_id': ticket_id,
                    'message': customer_message,
                    'sender_name': data.get('name', customer_email),
                    'sender_email': customer_email,
                    'sender_type': 'customer',
                    'is_customer': True,
                    'attachments': [],
                    'created_at': datetime.now()
                }
                db.create_reply(reply_data)
                logger.info(f"Customer reply saved for ticket {ticket_id}")
                
                # Update ticket status
                db.update_ticket(ticket_id, {
                    'has_unread_reply': True,
                    'last_reply_at': datetime.now(),
                    'status': 'Customer Replied'
                })
            
            # Update the ticket with the AI draft
            result = db.update_ticket(ticket_id, {
                'draft': ai_response,
                'n8n_draft': ai_response,
                'updated_at': datetime.now()
            })
            
            # Check if any document was actually modified
            updated_count = result.matched_count if hasattr(result, 'matched_count') else 0
            
            if updated_count == 0:
                logger.warning(f"No ticket found to update with ID {ticket_id}")
                return jsonify({
                    'success': False,
                    'message': f"Ticket {ticket_id} not found. Ensure 'from' (email) is sent for fallback lookup.",
                    'ticket_id': ticket_id,
                    'customer_reply_saved': False
                }), 404
            
            logger.info(f"AI draft saved for ticket {ticket_id}: {len(ai_response)} chars")
            
            return jsonify({
                'success': True,
                'message': 'AI response saved to ticket',
                'ticket_id': ticket_id,
                'draft_length': len(ai_response),
                'customer_reply_saved': bool(customer_message and customer_email and ticket),
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'message': 'AI response received (no ticket_id provided)',
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in display_response: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/get-response/<ticket_id>', methods=['GET'])
def get_ai_response(ticket_id):
    """
    Get AI-generated response for a specific ticket.
    
    Args:
        ticket_id: The ticket ID to generate response for
        
    Returns:
        JSON with AI-generated response
    """
    try:
        # Generate a mock AI response (replace with actual AI integration)
        mock_response = (
            f"Dear Customer,\n\n"
            f"Thank you for contacting AutoAssistGroup regarding ticket #{ticket_id}.\n\n"
            f"I have reviewed your request and I am looking into it immediately. "
            f"We usually resolve issues like this within 24 hours.\n\n"
            f"Is there any additional information you can provide that might help us expedite this?\n\n"
            f"Best regards,\n"
            f"AutoAssist AI Support"
        )
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'ai_response': mock_response,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error generating AI response for ticket {ticket_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/health', methods=['GET'])
def ai_health():
    """Health check for AI service."""
    return jsonify({
        'status': 'healthy',
        'service': 'ai',
        'timestamp': datetime.now().isoformat()
    })
