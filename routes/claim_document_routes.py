"""
Claim Document Routes Blueprint

This module contains API endpoints for managing claim documents
(receipts, photos, etc.) attached to tickets.

Author: AutoAssistGroup Development Team
"""

from flask import Blueprint, request, jsonify, send_file
import logging
from datetime import datetime
import io
import base64
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

claim_document_bp = Blueprint('claim_document', __name__, url_prefix='/api')


@claim_document_bp.route('/tickets/<ticket_id>/claim-documents', methods=['GET'])
def get_claim_documents(ticket_id):
    """
    Get all claim documents for a specific ticket.
    
    Returns:
        JSON with list of claim documents
    """
    try:
        from database import get_db
        db = get_db()
        
        # Get all documents for this ticket
        documents = list(db.claim_documents.find({
            'ticket_id': ticket_id,
            'is_deleted': {'$ne': True}
        }))
        
        # Convert ObjectId to string for JSON serialization
        results = []
        for doc in documents:
            doc_data = {
                '_id': str(doc['_id']),
                'ticket_id': doc.get('ticket_id'),
                'file_name': doc.get('file_name', 'Untitled'),
                'file_size': doc.get('file_size', 0),
                'file_type': doc.get('file_type', 'application/octet-stream'),
                'description': doc.get('description', ''),
                'uploaded_by': doc.get('uploaded_by', ''),
                'uploaded_at': doc.get('uploaded_at', datetime.now()).isoformat() if isinstance(doc.get('uploaded_at'), datetime) else str(doc.get('uploaded_at', ''))
            }
            results.append(doc_data)
            
        logger.info(f"Retrieved {len(results)} claim documents for ticket {ticket_id}")
        
        return jsonify({
            'success': True,
            'documents': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error getting claim documents for ticket {ticket_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve claim documents'
        }), 500


@claim_document_bp.route('/tickets/<ticket_id>/claim-documents', methods=['POST'])
def upload_claim_document(ticket_id):
    """
    Upload a new claim document for a ticket.
    
    Accepts:
        FormData with fields: file, description
    
    Returns:
        JSON with created document info
    """
    try:
        from database import get_db
        from flask import session
        db = get_db()
        
        # Verify ticket exists
        ticket = db.tickets.find_one({'ticket_id': ticket_id})
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket not found'
            }), 404
        
        # Handle file upload
        file = request.files.get('file')
        if not file:
            return jsonify({
                'success': False,
                'message': 'File is required'
            }), 400
        
        description = request.form.get('description', '').strip()
        
        file_name = file.filename
        file_type = file.content_type or 'application/octet-stream'
        
        # Read and encode file as base64 for storage
        file_bytes = file.read()
        file_size = len(file_bytes)
        file_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Get current user from session
        uploaded_by = session.get('user_id', 'unknown')
        
        # Create document record
        doc_data = {
            'ticket_id': ticket_id,
            'file_name': file_name,
            'file_size': file_size,
            'file_type': file_type,
            'file_data': file_data,
            'description': description,
            'uploaded_by': uploaded_by,
            'uploaded_at': datetime.now(),
            'is_deleted': False
        }
        
        result = db.claim_documents.insert_one(doc_data)
        
        logger.info(f"Uploaded claim document '{file_name}' for ticket {ticket_id} (ID: {result.inserted_id})")
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document': {
                '_id': str(result.inserted_id),
                'file_name': file_name,
                'file_size': file_size,
                'file_type': file_type,
                'description': description,
                'uploaded_at': datetime.now().isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading claim document for ticket {ticket_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to upload document'
        }), 500


@claim_document_bp.route('/tickets/<ticket_id>/claim-documents/<document_id>', methods=['DELETE'])
def delete_claim_document(ticket_id, document_id):
    """
    Delete a claim document (soft delete).
    
    Returns:
        JSON with success status
    """
    try:
        from database import get_db
        db = get_db()
        
        doc = db.claim_documents.find_one({
            '_id': ObjectId(document_id),
            'ticket_id': ticket_id
        })
        
        if not doc:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        # Soft delete
        db.claim_documents.update_one(
            {'_id': ObjectId(document_id)},
            {'$set': {'is_deleted': True, 'deleted_at': datetime.now()}}
        )
        
        logger.info(f"Soft-deleted claim document {document_id} from ticket {ticket_id}")
        
        return jsonify({
            'success': True,
            'message': 'Document deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting claim document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to delete document'
        }), 500


@claim_document_bp.route('/tickets/<ticket_id>/claim-documents/<document_id>/download', methods=['GET'])
def download_claim_document(ticket_id, document_id):
    """
    Download a claim document file.
    
    Returns:
        File download response
    """
    try:
        from database import get_db
        db = get_db()
        
        doc = db.claim_documents.find_one({
            '_id': ObjectId(document_id),
            'ticket_id': ticket_id,
            'is_deleted': {'$ne': True}
        })
        
        if not doc:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        file_data = doc.get('file_data')
        file_name = doc.get('file_name', 'document')
        file_type = doc.get('file_type', 'application/octet-stream')
        
        if file_data:
            try:
                binary_data = base64.b64decode(file_data)
                return send_file(
                    io.BytesIO(binary_data),
                    download_name=file_name,
                    mimetype=file_type,
                    as_attachment=True
                )
            except Exception as decode_error:
                logger.error(f"Error decoding file data: {decode_error}")
                return jsonify({
                    'success': False,
                    'message': 'Error decoding file data'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'No file data available'
            }), 404
        
    except Exception as e:
        logger.error(f"Error downloading claim document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to download document'
        }), 500


@claim_document_bp.route('/tickets/<ticket_id>/vehicle-info', methods=['PUT'])
def update_vehicle_info(ticket_id):
    """
    Update vehicle and claim information for a ticket.
    
    Accepts:
        JSON with fields: vehicle_registration, service_date, claim_date, 
                         type_of_claim, technician, vhc_link
    
    Returns:
        JSON with success status
    """
    try:
        from database import get_db
        db = get_db()
        
        # Verify ticket exists
        ticket = db.tickets.find_one({'ticket_id': ticket_id})
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket not found'
            }), 404
        
        data = request.get_json()
        
        update_data = {
            'updated_at': datetime.now()
        }
        
        # Update only the fields that are provided
        allowed_fields = [
            'vehicle_registration', 'service_date', 'claim_date',
            'type_of_claim', 'technician', 'vhc_link',
            'days_between_service_claim', 'advisories_followed',
            'within_warranty', 'new_fault_codes', 'dpf_light_on', 'eml_light_on'
        ]
        
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        db.tickets.update_one(
            {'ticket_id': ticket_id},
            {'$set': update_data}
        )
        
        logger.info(f"Updated vehicle info for ticket {ticket_id}")
        
        return jsonify({
            'success': True,
            'message': 'Vehicle information updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating vehicle info for ticket {ticket_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to update vehicle information'
        }), 500
