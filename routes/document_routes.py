"""
Document Routes Blueprint

This module contains API endpoints for document management,
serving the common documents used in ticket responses.

Author: AutoAssistGroup Development Team
"""

from flask import Blueprint, request, jsonify, send_file
import logging
from datetime import datetime
import os
import io
import base64
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

document_bp = Blueprint('document', __name__, url_prefix='/api')


@document_bp.route('/common-documents', methods=['GET'])
def get_common_documents():
    """
    Get all common documents available for use.
    
    Returns:
        JSON with list of documents
    """
    try:
        from database import get_db
        db = get_db()
        
        # Get all active documents
        documents = list(db.common_documents.find({'is_active': {'$ne': False}}))
        
        # Convert ObjectId to string for JSON serialization
        results = []
        for doc in documents:
            doc_data = {
                '_id': str(doc['_id']),
                'name': doc.get('name', 'Untitled'),
                'type': doc.get('type', 'file'),
                'file_name': doc.get('file_name', ''),
                'file_size': doc.get('file_size', 0),
                'file_path': doc.get('file_path', ''),
                'created_at': doc.get('created_at', datetime.now()).isoformat() if isinstance(doc.get('created_at'), datetime) else str(doc.get('created_at', '')),
                'updated_at': doc.get('updated_at', datetime.now()).isoformat() if isinstance(doc.get('updated_at'), datetime) else str(doc.get('updated_at', '')),
                'description': doc.get('description', ''),
                'is_active': doc.get('is_active', True)
            }
            results.append(doc_data)
            
        logger.info(f"Retrieved {len(results)} common documents")
        
        return jsonify({
            'success': True,
            'documents': results,
            'count': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error getting common documents: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve documents'
        }), 500


@document_bp.route('/common-documents/<document_id>', methods=['GET'])
def get_single_document(document_id):
    """
    Get a single document by ID.
    
    Returns:
        JSON with document details
    """
    try:
        from database import get_db
        db = get_db()
        
        doc = db.common_documents.find_one({'_id': ObjectId(document_id)})
        
        if not doc:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        doc_data = {
            '_id': str(doc['_id']),
            'name': doc.get('name', 'Untitled'),
            'type': doc.get('type', 'file'),
            'file_name': doc.get('file_name', ''),
            'file_size': doc.get('file_size', 0),
            'file_path': doc.get('file_path', ''),
            'created_at': doc.get('created_at', datetime.now()).isoformat() if isinstance(doc.get('created_at'), datetime) else str(doc.get('created_at', '')),
            'updated_at': doc.get('updated_at', datetime.now()).isoformat() if isinstance(doc.get('updated_at'), datetime) else str(doc.get('updated_at', '')),
            'description': doc.get('description', ''),
            'is_active': doc.get('is_active', True)
        }
        
        return jsonify({
            'success': True,
            'document': doc_data
        })
        
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to retrieve document'
        }), 500


@document_bp.route('/common-documents/<document_id>/download', methods=['GET'])
def download_document(document_id):
    """
    Download a document file.
    
    Returns:
        File download response
    """
    try:
        from database import get_db
        db = get_db()
        
        doc = db.common_documents.find_one({'_id': ObjectId(document_id)})
        
        if not doc:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        # Check if file data is stored in database (base64)
        file_data = doc.get('file_data')
        file_name = doc.get('file_name', 'document')
        file_path = doc.get('file_path', '')
        
        if file_data:
            # File stored as base64 in database
            try:
                binary_data = base64.b64decode(file_data)
                return send_file(
                    io.BytesIO(binary_data),
                    download_name=file_name,
                    as_attachment=True
                )
            except Exception as decode_error:
                logger.error(f"Error decoding file data: {decode_error}")
                return jsonify({
                    'success': False,
                    'message': 'Error decoding file data'
                }), 500
        elif file_path and os.path.exists(file_path):
            # File stored on filesystem
            return send_file(
                file_path,
                download_name=file_name,
                as_attachment=True
            )
        else:
            return jsonify({
                'success': False,
                'message': 'File not found or no file data available'
            }), 404
        
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to download document'
        }), 500


@document_bp.route('/common-documents', methods=['POST'])
def create_document():
    """
    Create a new common document with file upload.
    
    Accepts:
        FormData with fields: name, type, description, file
    
    Returns:
        JSON with created document
    """
    try:
        from database import get_db
        db = get_db()
        
        name = request.form.get('name', '').strip()
        doc_type = request.form.get('type', 'file')
        description = request.form.get('description', '').strip()
        
        if not name:
            return jsonify({
                'success': False,
                'message': 'Document name is required'
            }), 400
        
        # Handle file upload
        file = request.files.get('file')
        if not file:
            return jsonify({
                'success': False,
                'message': 'File is required for new documents'
            }), 400
        
        file_name = file.filename
        file_size = 0
        file_data = None
        
        # Read and encode file as base64 for storage
        file_bytes = file.read()
        file_size = len(file_bytes)
        file_data = base64.b64encode(file_bytes).decode('utf-8')
        
        # Create document record
        doc_data = {
            'name': name,
            'type': doc_type,
            'description': description,
            'file_name': file_name,
            'file_size': file_size,
            'file_data': file_data,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_active': True
        }
        
        result = db.common_documents.insert_one(doc_data)
        
        logger.info(f"Created new common document: {name} (ID: {result.inserted_id})")
        
        return jsonify({
            'success': True,
            'message': 'Document created successfully',
            'document_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to create document'
        }), 500


@document_bp.route('/common-documents/<document_id>', methods=['PUT'])
def update_document(document_id):
    """
    Update an existing common document.
    
    Accepts:
        JSON with fields: name, type, description
    
    Returns:
        JSON with updated document
    """
    try:
        from database import get_db
        db = get_db()
        
        doc = db.common_documents.find_one({'_id': ObjectId(document_id)})
        if not doc:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        data = request.get_json()
        
        update_data = {
            'updated_at': datetime.now()
        }
        
        if 'name' in data:
            update_data['name'] = data['name'].strip()
        if 'type' in data:
            update_data['type'] = data['type']
        if 'description' in data:
            update_data['description'] = data['description'].strip()
        
        db.common_documents.update_one(
            {'_id': ObjectId(document_id)},
            {'$set': update_data}
        )
        
        logger.info(f"Updated common document: {document_id}")
        
        return jsonify({
            'success': True,
            'message': 'Document updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to update document'
        }), 500


@document_bp.route('/common-documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    Delete a common document (soft delete by setting is_active to False).
    
    Returns:
        JSON with success status
    """
    try:
        from database import get_db
        db = get_db()
        
        doc = db.common_documents.find_one({'_id': ObjectId(document_id)})
        if not doc:
            return jsonify({
                'success': False,
                'message': 'Document not found'
            }), 404
        
        # Soft delete - set is_active to False
        db.common_documents.update_one(
            {'_id': ObjectId(document_id)},
            {'$set': {'is_active': False, 'deleted_at': datetime.now()}}
        )
        
        logger.info(f"Soft-deleted common document: {document_id}")
        
        return jsonify({
            'success': True,
            'message': 'Document deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to delete document'
        }), 500

