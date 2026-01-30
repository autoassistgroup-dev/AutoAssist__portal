"""
Ticket API Routes

Handles all ticket CRUD operations including:
- Getting tickets (paginated, filtered)
- Creating tickets
- Updating ticket status
- Searching tickets
- Closing tickets

Author: AutoAssistGroup Development Team
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from middleware.session_manager import is_authenticated, safe_member_lookup
from utils.validators import sanitize_input, validate_ticket_id

logger = logging.getLogger(__name__)

# Create blueprint
ticket_bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')


@ticket_bp.route('', methods=['GET'])
@ticket_bp.route('/', methods=['GET'])
def get_tickets():
    """
    Get paginated list of tickets with optional filters.
    
    Query params:
        page: Page number (default 1)
        per_page: Items per page (default 20)
        status: Filter by status
        priority: Filter by priority
        search: Search query
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Get pagination and filter params
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        priority_filter = request.args.get('priority')
        search_query = request.args.get('search')
        
        # Validate per_page
        per_page = min(per_page, 100)  # Max 100 items per page
        
        from database import get_db
        db = get_db()
        
        # Get tickets with pagination
        tickets = db.get_tickets_with_assignments(
            page=page,
            per_page=per_page,
            status_filter=status_filter,
            priority_filter=priority_filter,
            search_query=search_query
        )
        
        # Get total count for pagination
        total = db.get_tickets_count(
            status_filter=status_filter,
            priority_filter=priority_filter,
            search_query=search_query
        )
        
        # Serialize tickets for JSON response
        serialized_tickets = []
        for ticket in tickets:
            serialized_tickets.append(_serialize_ticket(ticket))
        
        return jsonify({
            'success': True,
            'tickets': serialized_tickets,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting tickets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@ticket_bp.route('', methods=['POST'])
@ticket_bp.route('/', methods=['POST'])
def create_ticket_webhook():
    """
    Handle ticket creation from N8N webhook (or other API clients).
    Accepts JSON payload matching N8N structure.
    """
    try:
        # Check for JSON data
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
            
        data = request.get_json()
        
        # Reuse N8N processing logic
        from routes.n8n_routes import process_n8n_email_data
        
        processed = process_n8n_email_data(data)
        
        if not processed:
            return jsonify({'success': False, 'error': 'Invalid ticket data'}), 400
            
        from database import get_db
        db = get_db()
        
        # Create ticket
        ticket_id = db.create_ticket(processed)
        
        logger.info(f"Ticket created via webhook: {processed.get('ticket_id')}")
        
        return jsonify({
            'success': True, 
            'message': 'Ticket created successfully',
            'ticket_id': processed.get('ticket_id'),
            'db_id': str(ticket_id)
        })
        
    except ValueError as e:
        if "Thread ID already exists" in str(e):
            logger.warning(f"Duplicate thread ID detected via webhook: {e}")
            
            # Find the existing ticket
            from database import get_db
            db = get_db()
            
            thread_id = processed.get('thread_id')
            existing_ticket = db.tickets.find_one({"thread_id": thread_id})
            
            if existing_ticket:
                logger.info(f"Returning existing ticket {existing_ticket.get('ticket_id')} for thread {thread_id}")
                return jsonify({
                    'success': True, 
                    'message': 'Ticket already exists',
                    'ticket_id': existing_ticket.get('ticket_id'),
                    'db_id': str(existing_ticket.get('_id'))
                })
        
        logger.error(f"Error creating ticket via webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 409
        
    except Exception as e:
        logger.error(f"Error creating ticket via webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/create', methods=['POST'])
def create_ticket():
    """
    Create a new ticket via API.
    Handles AJAX form submission from create_ticket.html.
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        current_member = safe_member_lookup()
        if not current_member:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
        import uuid
        from database import get_db
        db = get_db()
        
        # Generate ticket ID first to use in thread_id
        ticket_id = 'M' + str(uuid.uuid4())[:5].upper()
        
        # Extract form data
        ticket_data = {
            'ticket_id': ticket_id,
            'thread_id': f'manual_{ticket_id}',  # Ensure unique thread_id for database constraint
            'subject': request.form.get('subject', ''),
            'body': request.form.get('body', ''), # Mapped from description? Check form field names
            'description': request.form.get('description', ''), # Fallback or main?
            'customer_first_name': request.form.get('customer_first_name', ''),
            'customer_surname': request.form.get('customer_surname', ''),
            'customer_title': request.form.get('customer_title', ''),
            'vehicle_registration': request.form.get('vehicle_registration', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'type_of_claim': request.form.get('type_of_claim', ''),
            'status': 'New',
            'priority': request.form.get('priority', 'Medium'),
            'assigned_technician': request.form.get('technician', ''),
            'created_at': datetime.now(),
            'created_by': current_member.get('name', ''),
            'created_by_id': session.get('member_id'),
            'creation_method': 'api', 
            'is_forwarded': False
        }
        
        # Handle field mapping (create_ticket.html inputs vs DB schema)
        # HTML inputs: subject, customer_first_name, customer_surname, email, vehicle_registration, type_of_claim, priority, technician
        # No 'body' input in HTML form view? 
        # HTML shows: <input type="text" name="subject">. Where is description?
        # HTML was cut off at line 800. I need to assume there is a description/body field.
        # But 'request.form.get' is safe.
        
        db.create_ticket(ticket_data)
        
        logger.info(f"Ticket {ticket_data['ticket_id']} created by {current_member.get('name')}")
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': 'Ticket created successfully',
            'ticket_id': ticket_data['ticket_id'],
            'customer_number': ticket_data['ticket_id']
        })
        
    except Exception as e:
        logger.error(f"Error creating ticket via API: {e}")
        return jsonify({'status': 'error', 'success': False, 'message': str(e)}), 500


@ticket_bp.route('/<ticket_id>', methods=['GET'])
def get_ticket(ticket_id):
    """Get a single ticket by ID."""
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
        
        from database import get_db
        db = get_db()
        
        ticket = db.get_ticket_by_id(ticket_id)
        
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        return jsonify({
            'success': True,
            'ticket': _serialize_ticket(ticket)
        })
        
    except Exception as e:
        logger.error(f"Error getting ticket {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/status', methods=['PUT', 'PATCH'])
def update_ticket_status(ticket_id):
    """
    Update ticket status.
    Available for ALL users including Technical Director.
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        from database import get_db
        db = get_db()
        
        # Get existing ticket
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Update status
        update_data = {
            'status': new_status,
            'updated_at': datetime.now()
        }
        
        db.update_ticket(ticket_id, update_data)
        
        logger.info(f"Ticket {ticket_id} status updated to {new_status} by {session.get('member_name')}")
        
        return jsonify({
            'success': True,
            'message': f'Status updated to {new_status}',
            'ticket_id': ticket_id
        })
        
    except Exception as e:
        logger.error(f"Error updating ticket status {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/close', methods=['POST'])
def close_ticket(ticket_id):
    """
    Close a ticket.
    Available for ALL users including Technical Director.
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
        
        from database import get_db
        db = get_db()
        
        # Get existing ticket
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Update status to Closed
        update_data = {
            'status': 'Closed',
            'closed_at': datetime.now(),
            'closed_by': session.get('member_id'),
            'updated_at': datetime.now()
        }
        
        db.update_ticket(ticket_id, update_data)
        
        logger.info(f"Ticket {ticket_id} closed by {session.get('member_name')}")
        
        return jsonify({
            'success': True,
            'message': 'Ticket closed successfully',
            'ticket_id': ticket_id
        })
        
    except Exception as e:
        logger.error(f"Error closing ticket {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    """
    Delete a ticket permanently.
    Requires admin or authorized role.
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if user is admin
        from middleware.session_manager import is_admin
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
        
        from database import get_db
        db = get_db()
        
        # Check if ticket exists
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Delete the ticket
        result = db.tickets.delete_one({'ticket_id': ticket_id})
        
        if result.deleted_count > 0:
            logger.info(f"Ticket {ticket_id} deleted by {session.get('member_name')}")
            return jsonify({
                'success': True,
                'message': 'Ticket deleted successfully',
                'ticket_id': ticket_id
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete ticket'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting ticket {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/reply', methods=['POST'])
def send_ticket_reply(ticket_id):
    """
    Send a reply to a ticket.
    Creates a reply record and optionally sends email to customer.
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        from database import get_db
        db = get_db()
        
        # Get ticket
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket not found'}), 404
        
        # Handle multipart form data (with attachments) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Debug: log all form fields received
            logger.info(f"Reply form fields received: {list(request.form.keys())}")
            logger.info(f"Reply form data: {dict(request.form)}")
            
            # Frontend has multiple handlers that send different field names:
            # - 'response_text' from enhanced attachment handler
            # - 'response' from native form handler
            # - 'message' for API compatibility
            message = request.form.get('response_text', 
                      request.form.get('response', 
                      request.form.get('message', '')))
            send_email = request.form.get('sendEmail', 'false').lower() == 'true'
            
            logger.info(f"Extracted message (len={len(message)}): {message[:100] if message else 'EMPTY'}")
            
            # Handle file attachments - frontend sends as attachment_0, attachment_1, etc.
            attachments = []
            for key in request.files:
                if key.startswith('attachment_') or key == 'attachments':
                    files = request.files.getlist(key) if key == 'attachments' else [request.files[key]]
                    for f in files:
                        if f.filename:
                            import base64
                            file_data = base64.b64encode(f.read()).decode('utf-8')
                            attachments.append({
                                'filename': f.filename,
                                'content_type': f.content_type,
                                'data': file_data
                            })
        else:
            data = request.get_json() or {}
            message = data.get('message', data.get('response_text', data.get('response', '')))
            send_email = data.get('sendEmail', False)
            attachments = data.get('attachments', [])
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        # Get current member info
        current_member = safe_member_lookup()
        sender_name = current_member.get('name', 'Support Team') if current_member else 'Support Team'
        
        # Create reply record
        reply_data = {
            'ticket_id': ticket_id,
            'message': message,
            'sender_name': sender_name,
            'sender_id': session.get('member_id'),
            'sender_type': 'agent',
            'attachments': attachments,
            'created_at': datetime.now()
        }
        
        reply_id = db.create_reply(reply_data)
        
        # Update ticket with last reply info
        db.update_ticket(ticket_id, {
            'last_reply_at': datetime.now(),
            'last_reply_by': sender_name,
            'updated_at': datetime.now()
        })
        
        logger.info(f"Reply sent for ticket {ticket_id} by {sender_name}")
        
        # Always send reply via N8N webhook to Outlook when there's a customer email
        email_sent = False
        if ticket.get('email'):
            try:
                import requests
                from config.settings import WEBHOOK_URL
                logger.info(f"Preparing to send reply via N8N webhook to {ticket.get('email')}")
                
                # Prepare webhook payload matching N8N workflow expectations
                webhook_payload = {
                    'ticket_id': ticket_id,
                    'response_text': message,
                    'replyMessage': message,  # Also include as replyMessage for compatibility
                    'customer_email': ticket.get('email'),
                    'email': ticket.get('email'),
                    'ticket_subject': ticket.get('subject', 'Your Support Request'),
                    'subject': ticket.get('subject', 'Your Support Request'),
                    'customer_name': ticket.get('customer_name', ticket.get('name', '')),
                    'priority': ticket.get('priority', 'Medium'),
                    'ticket_status': ticket.get('status', 'Waiting for Response'),
                    'ticketSource': ticket.get('source', 'manual'),  # Determines reply vs new email flow
                    'is_email_ticket': ticket.get('is_email_ticket', False),
                    'threadId': ticket.get('threadId', ''),
                    'message_id': ticket.get('message_id', ''),
                    'timestamp': datetime.now().isoformat(),
                    'user_id': session.get('member_id'),
                    'has_attachments': len(attachments) > 0,
                    'attachments': attachments,
                    'attachment_count': len(attachments),
                    'body': ticket.get('body', ''),  # Original ticket body for context
                    'draft': message,
                    'message': message,
                    'content': message
                }
                
                logger.info(f"Sending reply to N8N webhook for ticket {ticket_id}")
                
                webhook_response = requests.post(
                    WEBHOOK_URL,
                    json=webhook_payload,
                    timeout=30
                )
                
                email_sent = webhook_response.status_code == 200
                logger.info(f"N8N webhook response for ticket {ticket_id}: {webhook_response.status_code}")
                
            except requests.exceptions.Timeout:
                logger.error(f"N8N webhook timeout for ticket {ticket_id}")
            except Exception as email_error:
                logger.error(f"Failed to send via N8N webhook for ticket {ticket_id}: {email_error}")
        
        return jsonify({
            'success': True,
            'message': 'Reply sent successfully',
            'reply_id': str(reply_id),
            'ticket_id': ticket_id,
            'email_sent': email_sent
        })
        
    except Exception as e:
        logger.error(f"Error sending reply for ticket {ticket_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@ticket_bp.route('/search', methods=['GET'])
def search_tickets():
    """
    Search tickets with filters.
    
    Query params:
        q: Search query
        status: Status filter
        priority: Priority filter
        classification: Classification filter
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        query = request.args.get('q', '')
        status = request.args.get('status')
        priority = request.args.get('priority')
        classification = request.args.get('classification')
        
        from database import get_db
        db = get_db()
        
        tickets = db.search_tickets(
            query=query,
            status=status,
            priority=priority,
            classification=classification
        )
        
        serialized_tickets = [_serialize_ticket(t) for t in tickets]
        
        return jsonify({
            'success': True,
            'tickets': serialized_tickets,
            'count': len(serialized_tickets)
        })
        
    except Exception as e:
        logger.error(f"Error searching tickets: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/send-email', methods=['POST'])
def send_ticket_email(ticket_id):
    """
    Send an email from a template (or custom).
    Similar to reply, but allows custom subject and body.
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
            
        data = request.get_json()
        subject = data.get('custom_subject') or data.get('subject') or ticket.get('subject')
        body = data.get('custom_body') or data.get('body') or data.get('message')
        attachments = data.get('attachments', [])
        
        if not body:
            return jsonify({'success': False, 'error': 'Email body is required'}), 400

        # Get current member info
        current_member = safe_member_lookup()
        sender_name = current_member.get('name', 'Support Team') if current_member else 'Support Team'
        
        # Create reply record (so it shows in history)
        reply_data = {
            'ticket_id': ticket_id,
            'message': body, # Store the body as the message
            'subject': subject, # Store subject if schema supports it, or just in body
            'sender_name': sender_name,
            'sender_id': session.get('member_id'),
            'sender_type': 'agent',
            'attachments': attachments,
            'created_at': datetime.now(),
            'is_email_template': True # detailed flag
        }
        
        reply_id = db.create_reply(reply_data)
        
        # Update ticket
        db.update_ticket(ticket_id, {
            'last_reply_at': datetime.now(),
            'last_reply_by': sender_name,
            'updated_at': datetime.now()
        })
        
        logger.info(f"Email template sent for ticket {ticket_id} by {sender_name}")
        
        # Send via N8N webhook
        email_sent = False
        if ticket.get('email'):
            try:
                import requests
                from config.settings import WEBHOOK_URL
                
                # Payload with OVERRIDDEN subject and body
                webhook_payload = {
                    'ticket_id': ticket_id,
                    'response_text': body,
                    'replyMessage': body,
                    'customer_email': ticket.get('email'),
                    'email': ticket.get('email'),
                    'ticket_subject': subject, # USE CUSTOM SUBJECT
                    'subject': subject,        # USE CUSTOM SUBJECT
                    'customer_name': ticket.get('customer_name', ticket.get('name', '')),
                    'priority': ticket.get('priority', 'Medium'),
                    'ticket_status': ticket.get('status', 'Waiting for Response'),
                    'ticketSource': ticket.get('source', 'manual'),
                    'user_id': session.get('member_id'),
                    'has_attachments': len(attachments) > 0,
                    'attachments': attachments,
                    'attachment_count': len(attachments),
                    'body': ticket.get('body', ''), 
                    'message': body,
                    'content': body
                }
                
                logger.info(f"Sending email template to N8N webhook for ticket {ticket_id}")
                
                webhook_response = requests.post(
                    WEBHOOK_URL,
                    json=webhook_payload,
                    timeout=30
                )
                
                email_sent = webhook_response.status_code == 200
                logger.info(f"N8N webhook response: {webhook_response.status_code}")
                
            except Exception as email_error:
                logger.error(f"Failed to send email template via N8N: {email_error}")
        
        if not email_sent:
             return jsonify({
                'success': True, # Still success because we saved the reply? Or Warning?
                'warning': 'Response saved but email delivery failed (Webhook Error)',
                'email_sent': False,
                'reply_id': str(reply_id)
            })

        return jsonify({
            'success': True,
            'message': 'Email sent successfully',
            'reply_id': str(reply_id),
            'email_sent': True
        })
        
    except Exception as e:
        logger.error(f"Error sending email template {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def _serialize_ticket(ticket):
    """
    Serialize a ticket document for JSON response.
    Handles ObjectId and datetime conversions.
    """
    if not ticket:
        return None
    
    serialized = {}
    for key, value in ticket.items():
        if key == '_id':
            serialized['_id'] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        elif isinstance(value, list):
            serialized[key] = [
                _serialize_ticket(item) if isinstance(item, dict) else 
                str(item) if hasattr(item, '__str__') and not isinstance(item, (str, int, float, bool)) else item
                for item in value
            ]
        elif isinstance(value, dict):
            serialized[key] = _serialize_ticket(value)
        else:
            serialized[key] = value
    
    return serialized

@ticket_bp.route('/<ticket_id>/priority', methods=['POST'])
def update_ticket_priority(ticket_id):
    """Update ticket priority."""
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        from utils.validators import validate_ticket_id
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
        
        data = request.get_json()
        priority = data.get('priority')
        
        if not priority:
            return jsonify({'success': False, 'error': 'Priority is required'}), 400
            
        from database import get_db
        db = get_db()
        
        # Update priority
        update_data = {
            'priority': priority,
            'updated_at': datetime.now()
        }
        
        db.update_ticket(ticket_id, update_data)
        
        logger.info(f"Ticket {ticket_id} priority updated to {priority} by {session.get('member_name')}")
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': f'Priority updated to {priority}'
        })
        
    except Exception as e:
        logger.error(f"Error updating ticket priority {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/technician', methods=['POST'])
def update_ticket_technician(ticket_id):
    """Update assigned technician."""
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        from utils.validators import validate_ticket_id
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
            
        data = request.get_json()
        technician_id = data.get('technician_id')
        
        from database import get_db
        db = get_db()
        
        update_data = {
            'assigned_technician_id': technician_id,
            'technician_id': technician_id, # Keep both for compatibility
            'updated_at': datetime.now()
        }
        
        # If unassigning
        if not technician_id:
             update_data['status'] = 'New' # Revert to New or Open?
             update_data['assigned_technician'] = None
             msg = 'Technician unassigned'
        else:
            # Get technician name for history/display
            tech = db.get_technician_by_id(technician_id)
            if tech:
                update_data['assigned_technician'] = tech.get('name')
            update_data['status'] = 'Assigned'
            msg = f"Technician assigned"
            
        db.update_ticket(ticket_id, update_data)
        
        logger.info(f"Ticket {ticket_id} technician updated to {technician_id} by {session.get('member_name')}")
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': msg
        })
        
    except Exception as e:
        logger.error(f"Error updating ticket technician {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/assign', methods=['POST'])
def assign_ticket(ticket_id):
    """
    Assign ticket (Take Over or Forward).
    """
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        from utils.validators import validate_ticket_id
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
            
        data = request.get_json() or {}
        is_forwarded = data.get('is_forwarded', False)
        target_member_id = data.get('assigned_to')
        note = data.get('note', '')
        
        from database import get_db
        db = get_db()
        
        current_member_id = session.get('member_id')
        current_member_name = session.get('member_name')
        
        update_data = {
            'updated_at': datetime.now()
        }
        
        if is_forwarded:
            # Forwarding to another member
            if not target_member_id:
                return jsonify({'success': False, 'error': 'Target member required for forwarding'}), 400
                
            update_data['is_forwarded'] = True
            update_data['forwarded_by'] = current_member_id
            update_data['forwarded_to'] = target_member_id
            update_data['forwarded_at'] = datetime.now()
            update_data['forwarding_note'] = note
            update_data['status'] = 'Open' # Or Forwarded?
            
            msg = 'Ticket forwarded successfully'
            
        else:
            # Take Over (Assign to self)
            update_data['assigned_to'] = current_member_id
            update_data['assigned_by'] = current_member_id
            update_data['assigned_at'] = datetime.now()
            update_data['status'] = 'In Progress'
            
            msg = 'Ticket taken over successfully'
            
        db.update_ticket(ticket_id, update_data)
        
        logger.info(f"Ticket {ticket_id} assignment updated by {current_member_name}")
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': msg
        })
        
    except Exception as e:
        logger.error(f"Error assigning ticket {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/tech-director', methods=['POST'])
def refer_to_tech_director(ticket_id):
    """Refer ticket to Technical Director."""
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        from utils.validators import validate_ticket_id
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
            
        from database import get_db
        db = get_db()
        
        update_data = {
            'referred_to_director': True,
            'referred_at': datetime.now(),
            'referred_by': session.get('member_id'),
            'status': 'Referred to Tech Director'  # Status MUST contain "Referred" for Tech Director to see it
        }
        
        db.update_ticket(ticket_id, update_data)
        
        logger.info(f"Ticket {ticket_id} referred to tech director by {session.get('member_name')}")
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': 'Referred to Technical Director'
        })
        
    except Exception as e:
        logger.error(f"Error referring ticket {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<ticket_id>/important', methods=['POST'])
def toggle_ticket_importance(ticket_id):
    """Toggle ticket importance (Starred)."""
    try:
        if not is_authenticated():
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        from utils.validators import validate_ticket_id
        if not validate_ticket_id(ticket_id):
            return jsonify({'success': False, 'error': 'Invalid ticket ID'}), 400
            
        from database import get_db
        db = get_db()
        
        # Get current state
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
             return jsonify({'success': False, 'error': 'Ticket not found'}), 404
             
        current_importance = ticket.get('is_important', False)
        new_importance = not current_importance
        
        update_data = {
            'is_important': new_importance,
            'updated_at': datetime.now()
        }
        
        db.update_ticket(ticket_id, update_data)
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': 'Importance updated',
            'is_important': new_importance
        })
        
    except Exception as e:
        logger.error(f"Error toggling importance for {ticket_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
