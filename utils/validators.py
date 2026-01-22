"""
Input Validation and Sanitization Utilities

Provides secure input handling functions for:
- XSS prevention
- Email validation
- Ticket ID validation

Author: AutoAssistGroup Development Team
"""

import re
import html


def sanitize_input(text):
    """
    Sanitize user input to prevent XSS attacks.
    
    Args:
        text: Raw user input text
        
    Returns:
        Escaped and stripped text safe for display
    """
    if not text:
        return ""
    return html.escape(str(text).strip())


def validate_email(email):
    """
    Validate email format using regex pattern.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email format is valid
    """
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_ticket_id(ticket_id):
    """
    Validate ticket ID format.
    
    Args:
        ticket_id: Ticket ID to validate
        
    Returns:
        bool: True if ticket ID format is valid
    """
    if not ticket_id or len(str(ticket_id)) > 50:
        return False
    # No spaces allowed in ticket IDs
    return str(ticket_id).replace(' ', '') == str(ticket_id)


def extract_email(raw_email):
    """
    Extract email address from possible formatted string.
    
    Handles formats like:
    - "John Doe <john@example.com>"
    - "john@example.com"
    
    Args:
        raw_email: Raw email string that may contain name
        
    Returns:
        Clean email address
    """
    if not raw_email:
        return ""
    
    # Try to extract email from "Name <email>" format
    match = re.search(r'<([^>]+)>', str(raw_email))
    if match:
        return match.group(1).strip()
    
    # Otherwise return the original stripped
    return str(raw_email).strip()


def extract_name_from_email(email_address):
    """
    Extract name from email address (part before @).
    
    Args:
        email_address: Email address string
        
    Returns:
        Name extracted from email or 'Unknown'
    """
    if not email_address:
        return "Unknown"
    
    try:
        # Extract part before @
        name_part = email_address.split('@')[0]
        # Replace common separators with spaces and title case
        name = name_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        return name.title()
    except Exception:
        return "Unknown"
