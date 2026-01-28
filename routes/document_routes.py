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
        
        # Get all documents
        # In the previous monorepo, documents might have been just files in a folder
        # or entries in a database. Based on database.py, we have a collection.
        
        # Check if collection exists and has documents
        documents = list(db.common_documents.find({}))
        
        # Convert ObjectId to string for JSON serialization
        results = []
        for doc in documents:
            doc_data = {
                '_id': str(doc['_id']),
                'name': doc.get('name', 'Untitled'),
                'type': doc.get('type', 'file'),
                'file_size': doc.get('file_size', 0),
                'created_at': doc.get('created_at', datetime.now()).isoformat() if isinstance(doc.get('created_at'), datetime) else doc.get('created_at'),
                'description': doc.get('description', '')
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
