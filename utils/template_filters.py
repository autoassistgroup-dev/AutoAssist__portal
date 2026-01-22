"""
Jinja2 Template Filters

Custom filters for use in templates including:
- Basename extraction
- Datetime formatting

Author: AutoAssistGroup Development Team
"""

import os
from utils.date_utils import safe_date_format


def get_basename(path):
    """
    Jinja2 filter to get basename of a path.
    
    Usage in template: {{ file_path | basename }}
    """
    if not path:
        return ""
    return os.path.basename(str(path))


def format_datetime(value, format_str="%b %d, %I:%M %p"):
    """
    Jinja2 filter to format datetime.
    
    Usage in template: {{ created_at | format_datetime }}
    """
    return safe_date_format(value, format_str)


def register_template_filters(app):
    """
    Register all custom Jinja2 filters with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.jinja_env.filters['basename'] = get_basename
    app.jinja_env.filters['format_datetime'] = format_datetime
    
    # Add more filters as needed
    app.jinja_env.filters['filesizeformat'] = filesizeformat


def filesizeformat(size_bytes):
    """Format file size in human readable format."""
    from utils.file_utils import format_file_size
    return format_file_size(size_bytes)
