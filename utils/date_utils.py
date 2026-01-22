"""
Date and Time Utilities

Provides date handling helpers for:
- Safe datetime parsing
- Date formatting
- Date grouping for dashboard

Author: AutoAssistGroup Development Team
"""

from datetime import datetime, timedelta


def safe_datetime_parse(value):
    """
    Safely parse datetime from either datetime object or string.
    
    Args:
        value: datetime object, ISO string, or None
        
    Returns:
        datetime object or None if parsing fails
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        # Try common datetime formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    
    return None


def safe_date_format(value, format_str="%b %d, %I:%M %p"):
    """
    Safely format datetime to string.
    
    Args:
        value: datetime object or parseable string
        format_str: Output format string
        
    Returns:
        Formatted date string or empty string if formatting fails
    """
    try:
        dt = safe_datetime_parse(value)
        if dt:
            return dt.strftime(format_str)
        return ""
    except Exception:
        return ""


def group_tickets_by_date(tickets):
    """
    Group tickets by date categories (Today, Yesterday, This Week, etc.).
    
    Args:
        tickets: List of ticket dictionaries with 'created_at' field
        
    Returns:
        dict: Tickets grouped by date category
    """
    if not tickets:
        return {}
    
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    groups = {
        'Today': [],
        'Yesterday': [],
        'This Week': [],
        'This Month': [],
        'Older': []
    }
    
    for ticket in tickets:
        created_at = ticket.get('created_at')
        dt = safe_datetime_parse(created_at)
        
        if not dt:
            groups['Older'].append(ticket)
            continue
        
        ticket_date = dt.date()
        
        if ticket_date == today:
            groups['Today'].append(ticket)
        elif ticket_date == yesterday:
            groups['Yesterday'].append(ticket)
        elif ticket_date > week_ago:
            groups['This Week'].append(ticket)
        elif ticket_date > month_ago:
            groups['This Month'].append(ticket)
        else:
            groups['Older'].append(ticket)
    
    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


def get_relative_time(dt):
    """
    Get relative time string (e.g., "2 hours ago").
    
    Args:
        dt: datetime object or parseable string
        
    Returns:
        Human-readable relative time string
    """
    if not dt:
        return "Unknown"
    
    parsed = safe_datetime_parse(dt)
    if not parsed:
        return "Unknown"
    
    now = datetime.now()
    diff = now - parsed
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
