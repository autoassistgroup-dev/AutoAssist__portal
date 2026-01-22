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
