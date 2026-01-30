"""
WebSocket Events Handler for Real-Time Updates

This module provides real-time communication using Flask-SocketIO for:
- New ticket notifications
- Live reply updates  
- Ticket status changes

Author: AutoAssistGroup Development Team
"""

import logging
from flask_socketio import SocketIO, emit, join_room, leave_room

logger = logging.getLogger(__name__)

# Initialize SocketIO (will be configured with app in init_socketio)
socketio = SocketIO()


def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode='eventlet',
        logger=False,
        engineio_logger=False
    )
    logger.info("[SOCKETIO] Initialized with eventlet async mode")
    return socketio


# ============== Connection Events ==============

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("[SOCKETIO] Client connected")
    emit('connected', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("[SOCKETIO] Client disconnected")


# ============== Room Management ==============

@socketio.on('join_ticket')
def handle_join_ticket(data):
    """Join a ticket-specific room for live updates"""
    ticket_id = data.get('ticket_id')
    if ticket_id:
        join_room(f'ticket_{ticket_id}')
        logger.info(f"[SOCKETIO] Client joined room: ticket_{ticket_id}")
        emit('joined_ticket', {'ticket_id': ticket_id})


@socketio.on('leave_ticket')
def handle_leave_ticket(data):
    """Leave a ticket-specific room"""
    ticket_id = data.get('ticket_id')
    if ticket_id:
        leave_room(f'ticket_{ticket_id}')
        logger.info(f"[SOCKETIO] Client left room: ticket_{ticket_id}")


@socketio.on('join_dashboard')
def handle_join_dashboard():
    """Join the dashboard room for new ticket notifications"""
    join_room('dashboard')
    logger.info("[SOCKETIO] Client joined dashboard room")
    emit('joined_dashboard', {'status': 'joined'})


# ============== Broadcast Functions ==============

def emit_new_ticket(ticket_data):
    """
    Broadcast new ticket to all connected clients on dashboard
    
    Args:
        ticket_data: dict containing ticket information
    """
    try:
        socketio.emit('new_ticket', ticket_data, room='dashboard')
        logger.info(f"[SOCKETIO] Emitted new_ticket: {ticket_data.get('ticket_id')}")
    except Exception as e:
        logger.error(f"[SOCKETIO] Error emitting new_ticket: {e}")


def emit_new_reply(ticket_id, reply_data):
    """
    Broadcast new reply to clients viewing the specific ticket
    
    Args:
        ticket_id: The ticket ID
        reply_data: dict containing reply information
    """
    try:
        socketio.emit('new_reply', reply_data, room=f'ticket_{ticket_id}')
        logger.info(f"[SOCKETIO] Emitted new_reply for ticket: {ticket_id}")
    except Exception as e:
        logger.error(f"[SOCKETIO] Error emitting new_reply: {e}")


def emit_ticket_update(ticket_id, update_data):
    """
    Broadcast ticket update (status, priority, etc.) to relevant clients
    
    Args:
        ticket_id: The ticket ID
        update_data: dict containing update information
    """
    try:
        # Emit to ticket room
        socketio.emit('ticket_updated', update_data, room=f'ticket_{ticket_id}')
        # Also emit to dashboard for list updates
        socketio.emit('ticket_updated', update_data, room='dashboard')
        logger.info(f"[SOCKETIO] Emitted ticket_updated for: {ticket_id}")
    except Exception as e:
        logger.error(f"[SOCKETIO] Error emitting ticket_updated: {e}")


def emit_reply_sent(ticket_id, reply_data):
    """
    Confirm reply was sent successfully (for sender's UI update)
    
    Args:
        ticket_id: The ticket ID
        reply_data: dict containing the sent reply
    """
    try:
        socketio.emit('reply_sent', reply_data, room=f'ticket_{ticket_id}')
        logger.info(f"[SOCKETIO] Emitted reply_sent for ticket: {ticket_id}")
    except Exception as e:
        logger.error(f"[SOCKETIO] Error emitting reply_sent: {e}")
