"""
File Handling Utilities

Provides file operation helpers for:
- File extension validation
- MIME type detection
- File type info with icons/colors
- File size formatting

Author: AutoAssistGroup Development Team
"""

import os
import mimetypes


# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'txt', 'csv'}


def allowed_file(filename):
    """
    Check if file extension is in allowed list.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        bool: True if file extension is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Human readable file size string (e.g., "1.5 MB")
    """
    if not size_bytes:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def get_mime_type(filename):
    """
    Get MIME type based on file extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        MIME type string or 'application/octet-stream' as fallback
    """
    if not filename:
        return 'application/octet-stream'
    
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'


def get_enhanced_file_type_info(filename, file_size=0):
    """
    Advanced file type detection with comprehensive MIME type mapping.
    Returns detailed file information including icons, colors, and capabilities.
    
    Args:
        filename: Name of the file
        file_size: Size of file in bytes (optional)
        
    Returns:
        dict: File information with icon, color, type, mime, viewable, category
    """
    extension = filename.split('.').pop().lower() if filename else ''
    
    file_type_mapping = {
        # Document types
        'pdf': {
            'icon': 'fas fa-file-pdf', 
            'color': 'text-red-600', 
            'type': 'PDF Document',
            'mime': 'application/pdf',
            'viewable': True,
            'category': 'document'
        },
        'doc': {
            'icon': 'fas fa-file-word', 
            'color': 'text-blue-600', 
            'type': 'Word Document',
            'mime': 'application/msword',
            'viewable': False,
            'category': 'document'
        },
        'docx': {
            'icon': 'fas fa-file-word', 
            'color': 'text-blue-600', 
            'type': 'Word Document',
            'mime': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'viewable': False,
            'category': 'document'
        },
        'xls': {
            'icon': 'fas fa-file-excel', 
            'color': 'text-green-600', 
            'type': 'Excel Spreadsheet',
            'mime': 'application/vnd.ms-excel',
            'viewable': False,
            'category': 'spreadsheet'
        },
        'xlsx': {
            'icon': 'fas fa-file-excel', 
            'color': 'text-green-600', 
            'type': 'Excel Spreadsheet',
            'mime': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'viewable': False,
            'category': 'spreadsheet'
        },
        'ppt': {
            'icon': 'fas fa-file-powerpoint', 
            'color': 'text-orange-600', 
            'type': 'PowerPoint Presentation',
            'mime': 'application/vnd.ms-powerpoint',
            'viewable': False,
            'category': 'presentation'
        },
        'pptx': {
            'icon': 'fas fa-file-powerpoint', 
            'color': 'text-orange-600', 
            'type': 'PowerPoint Presentation',
            'mime': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'viewable': False,
            'category': 'presentation'
        },
        # Image types
        'jpg': {
            'icon': 'fas fa-file-image', 
            'color': 'text-purple-600', 
            'type': 'JPEG Image',
            'mime': 'image/jpeg',
            'viewable': True,
            'category': 'image'
        },
        'jpeg': {
            'icon': 'fas fa-file-image', 
            'color': 'text-purple-600', 
            'type': 'JPEG Image',
            'mime': 'image/jpeg',
            'viewable': True,
            'category': 'image'
        },
        'png': {
            'icon': 'fas fa-file-image', 
            'color': 'text-purple-600', 
            'type': 'PNG Image',
            'mime': 'image/png',
            'viewable': True,
            'category': 'image'
        },
        'gif': {
            'icon': 'fas fa-file-image', 
            'color': 'text-purple-600', 
            'type': 'GIF Image',
            'mime': 'image/gif',
            'viewable': True,
            'category': 'image'
        },
        'webp': {
            'icon': 'fas fa-file-image', 
            'color': 'text-purple-600', 
            'type': 'WebP Image',
            'mime': 'image/webp',
            'viewable': True,
            'category': 'image'
        },
        # Archive types
        'zip': {
            'icon': 'fas fa-file-archive', 
            'color': 'text-yellow-600', 
            'type': 'ZIP Archive',
            'mime': 'application/zip',
            'viewable': False,
            'category': 'archive'
        },
        'rar': {
            'icon': 'fas fa-file-archive', 
            'color': 'text-yellow-600', 
            'type': 'RAR Archive',
            'mime': 'application/vnd.rar',
            'viewable': False,
            'category': 'archive'
        },
        '7z': {
            'icon': 'fas fa-file-archive', 
            'color': 'text-yellow-600', 
            'type': '7-Zip Archive',
            'mime': 'application/x-7z-compressed',
            'viewable': False,
            'category': 'archive'
        },
        # Text types
        'txt': {
            'icon': 'fas fa-file-alt', 
            'color': 'text-gray-600', 
            'type': 'Text File',
            'mime': 'text/plain',
            'viewable': True,
            'category': 'text'
        },
        'csv': {
            'icon': 'fas fa-file-csv', 
            'color': 'text-green-600', 
            'type': 'CSV File',
            'mime': 'text/csv',
            'viewable': True,
            'category': 'data'
        },
        'json': {
            'icon': 'fas fa-file-code', 
            'color': 'text-indigo-600', 
            'type': 'JSON File',
            'mime': 'application/json',
            'viewable': True,
            'category': 'data'
        },
        'xml': {
            'icon': 'fas fa-file-code', 
            'color': 'text-indigo-600', 
            'type': 'XML File',
            'mime': 'application/xml',
            'viewable': True,
            'category': 'data'
        }
    }
    
    file_info = file_type_mapping.get(extension, {
        'icon': 'fas fa-file', 
        'color': 'text-gray-600', 
        'type': 'File',
        'mime': 'application/octet-stream',
        'viewable': False,
        'category': 'unknown'
    })
    
    # Add file size information
    file_info['size'] = file_size
    file_info['size_formatted'] = format_file_size(file_size)
    file_info['extension'] = extension.upper()
    
    return file_info


def detect_warranty_form(filename, file_data=None):
    """
    Intelligent warranty form detection based on filename and content.
    Enhanced with comprehensive keyword matching.
    
    Args:
        filename: Name of the file
        file_data: Optional file content for content-based detection
        
    Returns:
        bool: True if file appears to be a warranty form
    """
    if not filename:
        return False
    
    # Comprehensive warranty keywords including common misspellings
    warranty_keywords = [
        'warranty', 'guarantee', 'warrantee', 'warrenty', 'guarante', 'garentee',
        'extended', 'protection', 'coverage', 'service_plan', 'service_contract',
        'maintenance_agreement', 'care_plan', 'support_plan', 'repair_coverage',
        'product_protection', 'extended_service', 'service_warranty', 
        'manufacturer_warranty', 'factory_warranty', 'vehicle_warranty',
        'bumper_to_bumper', 'powertrain', 'drivetrain', 'comprehensive_coverage',
        'dpf', 'diesel', 'emission', 'claim', 'form', 'customer',
        'repair', 'service', 'defect', 'malfunction', 'issue', 'fault',
        'warranty_form', 'warranty_claim', 'claim_form', 'service_form'
    ]
    
    filename_lower = filename.lower()
    
    # Check filename for warranty keywords
    for keyword in warranty_keywords:
        if keyword in filename_lower:
            return True
    
    # Future enhancement: Content-based analysis
    if file_data:
        # Framework for content analysis (OCR, text extraction, etc.)
        pass
    
    return False
