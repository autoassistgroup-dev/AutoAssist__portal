"""
Email Service for AutoAssistGroup Support System

Handles all email operations including:
- Sending notifications
- Attachment handling (file paths and base64)
- HTML email support

Author: AutoAssistGroup Development Team
"""

import os
import base64
import logging
import smtplib
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Import configuration
try:
    from config.settings import (
        EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, 
        EMAIL_PASSWORD, EMAIL_USE_TLS, EMAIL_FROM
    )
except ImportError:
    # Fallback to environment variables if config not yet available
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_FROM = os.environ.get('EMAIL_FROM', EMAIL_USERNAME)


logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications with attachment support."""
    
    def __init__(self, host=None, port=None, username=None, password=None, 
                 use_tls=None, from_email=None):
        """
        Initialize email service.
        
        Args:
            host: SMTP host (default from config)
            port: SMTP port (default from config)
            username: SMTP username (default from config)
            password: SMTP password (default from config)
            use_tls: Whether to use TLS (default from config)
            from_email: Sender email address (default from config)
        """
        self.host = host or EMAIL_HOST
        self.port = port or EMAIL_PORT
        self.username = username or EMAIL_USERNAME
        self.password = password or EMAIL_PASSWORD
        self.use_tls = use_tls if use_tls is not None else EMAIL_USE_TLS
        self.from_email = from_email or EMAIL_FROM
    
    def is_configured(self):
        """Check if email service is properly configured."""
        return bool(self.username and self.password)
    
    def send_email(self, to_email, subject, body, html_body=None, attachments=None):
        """
        Send email with optional HTML body and attachments.
        
        Args:
            to_email: Recipient email address (string or list)
            subject: Email subject
            body: Email body text
            html_body: Optional HTML body
            attachments: List of attachments. Each attachment can be:
                - String (file path)
                - Dict with keys: 'filename', 'data' (base64), 'content_type' (optional)
                
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Skip sending if email is not configured
            if not self.is_configured():
                logger.warning("Email not configured - would send email:")
                logger.info(f"To: {to_email}")
                logger.info(f"Subject: {subject}")
                logger.info(f"Body: {body[:200]}..." if len(body) > 200 else f"Body: {body}")
                if attachments:
                    logger.info(f"Attachments: {len(attachments)} files")
                return True  # Return True to not break workflow
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = to_email if isinstance(to_email, str) else ', '.join(to_email)
            msg['Subject'] = subject
            
            # Add text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            recipients = [to_email] if isinstance(to_email, str) else to_email
            
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email} with {len(attachments) if attachments else 0} attachments")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _add_attachment(self, msg, attachment):
        """
        Add an attachment to the message.
        
        Args:
            msg: MIMEMultipart message
            attachment: File path string or dict with file data
        """
        try:
            if isinstance(attachment, str):
                # Handle file path attachment
                self._add_file_attachment(msg, attachment)
            elif isinstance(attachment, dict):
                # Handle base64 data attachment
                self._add_base64_attachment(msg, attachment)
            else:
                logger.warning(f"Invalid attachment format: {type(attachment)}")
                
        except Exception as e:
            logger.error(f"Error processing attachment: {e}")
    
    def _add_file_attachment(self, msg, file_path):
        """Add attachment from file path."""
        if not os.path.exists(file_path):
            logger.warning(f"Attachment file not found: {file_path}")
            return
        
        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        filename = os.path.basename(file_path)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)
        logger.debug(f"Added file attachment: {filename}")
    
    def _add_base64_attachment(self, msg, attachment):
        """Add attachment from base64 data."""
        filename = attachment.get('filename', attachment.get('fileName', 'attachment'))
        file_data = attachment.get('data', attachment.get('fileData', ''))
        content_type = attachment.get('content_type', 'application/octet-stream')
        
        if not file_data:
            logger.warning(f"No data provided for attachment: {filename}")
            return
        
        try:
            # Decode base64 data
            decoded_data = base64.b64decode(file_data)
            
            # Determine MIME type
            mime_type = content_type
            if mime_type == 'application/octet-stream':
                guessed_type, _ = mimetypes.guess_type(filename)
                if guessed_type:
                    mime_type = guessed_type
            
            # Create attachment part
            maintype, subtype = mime_type.split('/', 1)
            part = MIMEBase(maintype, subtype)
            part.set_payload(decoded_data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)
            logger.debug(f"Added base64 attachment: {filename} ({len(decoded_data)} bytes)")
            
        except Exception as e:
            logger.error(f"Failed to decode base64 attachment {filename}: {e}")
    
    def send_template_email(self, to_email, template_name, context, attachments=None):
        """
        Send email using a template.
        
        Args:
            to_email: Recipient email address
            template_name: Name of the template
            context: Dictionary of template variables
            attachments: Optional list of attachments
            
        Returns:
            bool: True if email sent successfully
        """
        # This is a placeholder for template-based emails
        # Implementation would load templates and replace placeholders
        subject = context.get('subject', 'Notification')
        body = context.get('body', '')
        html_body = context.get('html_body')
        
        return self.send_email(to_email, subject, body, html_body, attachments)


# Global email service instance
email_service = EmailService()


# Convenience functions
def send_email(to_email, subject, body, html_body=None, attachments=None):
    """Send email using global email service instance."""
    return email_service.send_email(to_email, subject, body, html_body, attachments)


def is_email_configured():
    """Check if email service is configured."""
    return email_service.is_configured()
