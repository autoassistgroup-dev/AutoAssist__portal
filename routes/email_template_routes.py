"""
Email Template Routes Blueprint

This module handles the generation and retrieval of email templates
for the ticket detail view's email composition modal.

Author: AutoAssistGroup Development Team
"""

from flask import Blueprint, jsonify
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

email_template_bp = Blueprint('email_template', __name__, url_prefix='/api/email-template')


def generate_warranty_claim_template(ticket, customer_first_name):
    """Generate warranty claim template content"""
    return f"""Dear {customer_first_name},

Thank you for contacting Auto Assist Group regarding your warranty inquiry.

We have received your warranty claim and our Aftercare Team is reviewing the details. To process your claim efficiently, we may need some additional information:

• Vehicle registration number
• Current mileage reading (with dashboard photo)
• Any new fault codes or error messages
• Details of any recent services or repairs

Our warranty claim form is available at: https://autoassistgroup.com/report/claims

We will review your case within 2-3 business days and contact you with next steps. If your claim is approved, we will arrange the necessary remedial work at no cost to you.

If you have any questions in the meantime, please don't hesitate to contact us.

Best regards,
Auto Assist Group - Aftercare Team"""


def generate_technical_support_template(ticket, customer_first_name):
    """Generate technical support template content"""
    return f"""Dear {customer_first_name},

Thank you for reaching out regarding your technical issue.

We've received your inquiry and our technical team is reviewing the details. Based on the information provided, we will:

1. Assess the technical requirements for your vehicle
2. Provide you with a detailed solution and quote
3. Schedule the work at your convenience

Our technical specialists will contact you within 24 hours to discuss:
• Diagnostic findings and recommendations
• Service options and pricing
• Appointment availability

In the meantime, if you experience any urgent issues with your vehicle, please contact us immediately at 01234 567890.

Best regards,
Auto Assist Group - Technical Support Team"""


def generate_customer_service_template(ticket, customer_first_name):
    """Generate customer service template content"""
    return f"""Dear {customer_first_name},

Thank you for contacting Auto Assist Group.

We have received your inquiry and appreciate you choosing our services. Our customer service team is reviewing your request and will respond within 24 hours.

For immediate assistance, you can reach us at:
• Phone: 01234 567890 (Mon-Fri 8AM-6PM)
• Email: support@autoassistgroup.com

If you're looking to book a service, you can also use our online booking system at: https://autoassistgroup.com/book

We look forward to assisting you with your automotive needs.

Kind regards,
Auto Assist Group Customer Service Team"""


@email_template_bp.route('/<template_type>/<ticket_id>', methods=['GET'])
def get_email_template(template_type, ticket_id):
    """
    Get a specific email template populated with ticket data.
    
    Args:
        template_type: Type of template (warranty_claim, technical, etc.)
        ticket_id: ID of the ticket
        
    Returns:
        JSON with template data (subject, body, etc.)
    """
    try:
        from database import get_db
        db = get_db()
        
        # Get ticket details
        ticket = db.get_ticket_by_id(ticket_id)
        
        if not ticket:
            return jsonify({
                'status': 'error',
                'message': f'Ticket {ticket_id} not found'
            }), 404
            
        # Extract customer info
        customer_name = ticket.get('name', 'Customer').strip()
        first_name = customer_name.split()[0] if customer_name else 'Customer'
        
        # Determine subject
        original_subject = ticket.get('subject', 'Support Request')
        if not original_subject.lower().startswith('re:'):
            subject = f"Re: {original_subject} [TID: {ticket_id}]"
        else:
            subject = f"{original_subject} [TID: {ticket_id}]"
            
        # Check for existing draft
        draft = ticket.get('draft', '')
        has_draft = bool(draft)
        
        # Generate body based on template type
        body = ""
        content_source = "template"
        
        # NOTE: logic to prefer draft if highly relevant could go here,
        # but usually user selecting a template wants that specific template.
        
        if template_type == 'warranty_claim':
            body = generate_warranty_claim_template(ticket, first_name)
            subject = f"Re: Warranty Claim Update - Ticket #{ticket_id}"
            
        elif template_type == 'technical_support':
            body = generate_technical_support_template(ticket, first_name)
            
        elif template_type == 'customer_service':
            body = generate_customer_service_template(ticket, first_name)
            
        elif template_type == 'draft' and has_draft:
            # Explicit request for draft or fallback
            body = draft
            content_source = "draft"
            
        else:
            # Default fallback
            body = f"""Dear {first_name},

Thank you for contacting Auto Assist Group regarding ticket #{ticket_id}.

We have received your message and our team is reviewing it.

Best regards,
Auto Assist Group Support Team"""
        
        # Get attachments (if any were uploaded/generated)
        attachments = ticket.get('attachments', [])
        
        return jsonify({
            'status': 'success',
            'template': {
                'subject': subject,
                'body': body,
                'attachments': attachments,
                'has_draft': has_draft,
                'content_source': content_source,
                'template_type': template_type
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating email template: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
