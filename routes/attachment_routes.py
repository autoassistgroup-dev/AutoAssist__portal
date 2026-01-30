"""
Attachment Routes

Handles file attachment operations including:
- Downloading attachments
- Previewing attachments
- Serving uploaded files

Author: AutoAssistGroup Development Team
"""

import os
import base64
import logging
from flask import Blueprint, jsonify, request, send_file, make_response, Response
from io import BytesIO

from middleware.session_manager import is_authenticated
from utils.file_utils import get_mime_type

logger = logging.getLogger(__name__)

# Create blueprint
attachment_bp = Blueprint('attachments', __name__, url_prefix='/api/attachments')


@attachment_bp.route('/ticket/<ticket_id>/<int:attachment_index>', methods=['GET'])
def download_attachment(ticket_id, attachment_index):
    """
    Download attachments from multiple sources:
    1. Direct ticket attachments (base64 data)
    2. Reply attachments (webhook files)
    3. Metadata attachments (file uploads)
    """
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        
        from database import get_db
        db = get_db()
        
        # Get ticket
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Get attachments array
        attachments = ticket.get('attachments', [])
        
        if attachment_index < 0 or attachment_index >= len(attachments):
            return jsonify({'error': 'Attachment not found'}), 404
        
        attachment = attachments[attachment_index]
        
        # Get file data
        file_data = None
        filename = attachment.get('filename', attachment.get('fileName', 'download'))
        
        # Try to get base64 data
        if attachment.get('data') or attachment.get('fileData'):
            base64_data = attachment.get('data') or attachment.get('fileData')
            try:
                file_data = base64.b64decode(base64_data)
            except Exception as e:
                logger.error(f"Failed to decode base64: {e}")
        
        # If no data, try file path
        if not file_data and attachment.get('file_path'):
            file_path = attachment.get('file_path')
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
        
        if not file_data:
            return jsonify({'error': 'Attachment data not available'}), 404
        
        # Determine MIME type
        mime_type = get_mime_type(filename)
        
        # Create response
        response = make_response(file_data)
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = len(file_data)
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        return jsonify({'error': str(e)}), 500


@attachment_bp.route('/preview/<ticket_id>/<int:attachment_index>', methods=['GET'])
def preview_attachment(ticket_id, attachment_index):
    """Preview attachment inline (for images, PDFs, etc.)."""
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        
        from database import get_db
        db = get_db()
        
        # Get ticket
        ticket = db.get_ticket_by_id(ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Get attachments array
        attachments = ticket.get('attachments', [])
        
        if attachment_index < 0 or attachment_index >= len(attachments):
            return jsonify({'error': 'Attachment not found'}), 404
        
        attachment = attachments[attachment_index]
        
        # Get file data (same logic as download)
        file_data = None
        filename = attachment.get('filename', attachment.get('fileName', 'file'))
        
        if attachment.get('data') or attachment.get('fileData'):
            base64_data = attachment.get('data') or attachment.get('fileData')
            try:
                file_data = base64.b64decode(base64_data)
            except Exception:
                pass
        
        if not file_data and attachment.get('file_path'):
            file_path = attachment.get('file_path')
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
        
        if not file_data:
            return jsonify({'error': 'Attachment data not available'}), 404
        
        # Determine MIME type
        mime_type = get_mime_type(filename)
        
        # Create response for inline display
        response = make_response(file_data)
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error previewing attachment: {e}")
        return jsonify({'error': str(e)}), 500


@attachment_bp.route('/reply/<reply_id>/<int:attachment_index>', methods=['GET'])
def download_reply_attachment(reply_id, attachment_index):
    """Download attachment from a specific reply."""
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        
        from database import get_db
        from bson.objectid import ObjectId
        db = get_db()
        
        # Get reply
        logger.info(f"Looking for reply with ID: {reply_id}")
        reply = db.replies.find_one({'_id': ObjectId(reply_id)})
        if not reply:
            logger.error(f"Reply not found: {reply_id}")
            return jsonify({'error': 'Reply not found'}), 404
        logger.info(f"Reply found, has {len(reply.get('attachments', []))} attachments")
        
        # Get attachments
        attachments = reply.get('attachments', [])
        
        if attachment_index < 0 or attachment_index >= len(attachments):
            return jsonify({'error': 'Attachment not found'}), 404
        
        attachment = attachments[attachment_index]
        
        # Get file data
        file_data = None
        filename = attachment.get('filename', attachment.get('fileName', 'download'))
        logger.info(f"Attachment {attachment_index}: filename={filename}, has_data={bool(attachment.get('data'))}, has_fileData={bool(attachment.get('fileData'))}")
        
        if attachment.get('data') or attachment.get('fileData'):
            base64_data = attachment.get('data') or attachment.get('fileData')
            try:
                file_data = base64.b64decode(base64_data)
                logger.info(f"Successfully decoded {len(file_data)} bytes")
            except Exception as e:
                logger.error(f"Failed to decode base64 data: {e}")
        
        if not file_data:
            logger.error(f"No attachment data available for {filename}")
            return jsonify({'error': 'Attachment data not available'}), 404
        
        mime_type = get_mime_type(filename)
        
        response = make_response(file_data)
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading reply attachment: {e}")
        return jsonify({'error': str(e)}), 500


@attachment_bp.route('/reply/<reply_id>/<int:attachment_index>/preview', methods=['GET'])
def preview_reply_attachment(reply_id, attachment_index):
    """Preview attachment from a specific reply inline."""
    try:
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        
        from database import get_db
        from bson.objectid import ObjectId
        db = get_db()
        
        # Get reply
        logger.info(f"[PREVIEW] Looking for reply with ID: {reply_id}")
        reply = db.replies.find_one({'_id': ObjectId(reply_id)})
        if not reply:
            logger.error(f"[PREVIEW] Reply not found: {reply_id}")
            return jsonify({'error': 'Reply not found'}), 404
        logger.info(f"[PREVIEW] Reply found, has {len(reply.get('attachments', []))} attachments")
        
        # Get attachments
        attachments = reply.get('attachments', [])
        
        if attachment_index < 0 or attachment_index >= len(attachments):
            return jsonify({'error': 'Attachment not found'}), 404
        
        attachment = attachments[attachment_index]
        
        # Get file data
        file_data = None
        filename = attachment.get('filename', attachment.get('fileName', 'preview'))
        logger.info(f"[PREVIEW] Attachment {attachment_index}: filename={filename}, has_data={bool(attachment.get('data'))}, has_fileData={bool(attachment.get('fileData'))}")
        
        if attachment.get('data') or attachment.get('fileData'):
            base64_data = attachment.get('data') or attachment.get('fileData')
            try:
                import base64
                file_data = base64.b64decode(base64_data)
                logger.info(f"[PREVIEW] Successfully decoded {len(file_data)} bytes")
            except Exception as e:
                logger.error(f"[PREVIEW] Failed to decode base64: {e}")
        
        if not file_data:
            logger.error(f"[PREVIEW] No attachment data available for {filename}")
            return jsonify({'error': 'Attachment data not available'}), 404
        
        from utils.file_utils import get_mime_type
        mime_type = get_mime_type(filename)
        
        response = make_response(file_data)
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error previewing reply attachment: {e}")
        return jsonify({'error': str(e)}), 500
