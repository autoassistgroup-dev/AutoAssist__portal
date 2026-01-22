"""
Main Page Routes

Handles all page routes for the application including:
- Index/Tickets list
- Dashboard
- Ticket detail
- Create ticket
- Status page
- Members page
- Technicians page
- Admin panel
- Tech Director dashboard

Author: AutoAssistGroup Development Team
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from middleware.session_manager import safe_member_lookup, is_authenticated

logger = logging.getLogger(__name__)

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Main tickets list page."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member:
        return redirect(url_for('auth.login'))
    
    from database import get_db
    db = get_db()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status_filter = request.args.get('status', 'All')
    priority_filter = request.args.get('priority', 'All')
    search_query = request.args.get('search', '')
    
    tickets = db.get_tickets_with_assignments(
        page=page, 
        per_page=per_page,
        status_filter=status_filter if status_filter != 'All' else None,
        priority_filter=priority_filter if priority_filter != 'All' else None,
        search_query=search_query if search_query else None
    )
    
    total_count = db.get_tickets_count(
        status_filter=status_filter if status_filter != 'All' else None,
        priority_filter=priority_filter if priority_filter != 'All' else None,
        search_query=search_query if search_query else None
    )
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    members = db.get_all_members()
    technicians = list(db.technicians.find({"is_active": True}))
    ticket_statuses = list(db.ticket_statuses.find({"is_active": True}).sort("order", 1))
    
    # Calculate ALL stats from database
    all_tickets_db = list(db.tickets.find({}))
    
    # Initialize counters
    priorities = {'Urgent': 0, 'Fast': 0, 'High': 0, 'Medium': 0, 'Low': 0}
    classifications = {'Technical Issue': 0, 'Payment': 0, 'Support': 0, 'Warranty Claim': 0, 'Spam': 0, 'Account': 0}
    status_counts = {}
    open_tickets = 0
    waiting_tickets = 0
    resolved_tickets = 0
    forwarded_tickets = []
    
    current_member_name = current_member.get('name', '')
    
    for ticket in all_tickets_db:
        # Count priorities
        priority = ticket.get('priority', 'Medium')
        if priority in priorities:
            priorities[priority] += 1
        
        # Count classifications
        classification = ticket.get('classification', 'General')
        if classification in classifications:
            classifications[classification] += 1
        
        # Count statuses
        status = ticket.get('status', 'Open')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by status type
        if status == 'Open' or status == 'New':
            open_tickets += 1
        elif 'Waiting' in status:
            waiting_tickets += 1
        elif status in ['Resolved', 'Closed']:
            resolved_tickets += 1
        
        # Check for forwarded tickets
        if ticket.get('is_forwarded') and ticket.get('assigned_to') == current_member_name:
            forwarded_tickets.append(ticket)
    
    total_tickets = len(all_tickets_db)
    
    pagination = {
        'current_page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'total_count': total_count,
        'total_tickets': total_tickets,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search_query': search_query
    }
    
    return render_template('index.html',
                          tickets=tickets,
                          all_tickets=tickets,
                          current_member=current_member,
                          current_user=current_member.get('name') or session.get('member_name') or 'User',
                          current_user_role=current_member.get('role') or session.get('member_role') or 'User',
                          members=members,
                          technicians=technicians,
                          ticket_statuses=ticket_statuses,
                          priorities=priorities,
                          classifications=classifications,
                          status_counts=status_counts,
                          total_tickets=total_tickets,
                          open_tickets=open_tickets,
                          waiting_tickets=waiting_tickets,
                          resolved_tickets=resolved_tickets,
                          forwarded_tickets=forwarded_tickets,
                          pagination=pagination)


@main_bp.route('/dashboard')
def dashboard():
    """Main dashboard with full analytics."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member:
        return redirect(url_for('auth.login'))
    
    from database import get_db
    db = get_db()
    
    # Get base data
    tickets = db.get_tickets_with_assignments(page=1, per_page=50)
    members = db.get_all_members()
    technicians = list(db.technicians.find({"is_active": True}))
    ticket_statuses = list(db.ticket_statuses.find({"is_active": True}).sort("order", 1))
    
    # Initialize all template variables with defaults
    status_counts = {}
    overdue_tickets = []
    unread_tickets = []
    open_1_3_days = []
    open_today = []
    avg_resolution_time = 24
    total_claims = 0
    approved_claims = 0
    declined_claims = 0
    referred_claims = 0
    approved_percent = 0
    declined_percent = 0
    referred_percent = 0
    rejection_reasons = {
        'uncompleted_advisories': 0,
        'no_fault_code': 0,
        'warranty_expired': 0
    }
    team_performance = {}
    
    try:
        all_tickets_db = list(db.tickets.find({}))
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for ticket in all_tickets_db:
            # Status counts
            status = ticket.get('status', 'New')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by status type for claims
            if 'Approved' in status or 'Revisit' in status:
                approved_claims += 1
            elif 'Declined' in status or 'Not Covered' in status:
                declined_claims += 1
            elif 'Referred' in status:
                referred_claims += 1
            
            # Time-based categorization
            created_at = ticket.get('created_at')
            if created_at and status not in ['Closed', 'Resolved']:
                if isinstance(created_at, datetime):
                    days_old = (now - created_at).days
                    
                    if days_old > 3:
                        overdue_tickets.append(ticket)
                    elif days_old >= 1 and days_old <= 3:
                        open_1_3_days.append(ticket)
                    elif created_at >= today_start:
                        open_today.append(ticket)
            
            # Unread tickets
            if ticket.get('has_unread_reply'):
                unread_tickets.append(ticket)
            
            # Team performance - count by assigned technician
            assigned = ticket.get('assigned_technician') or ticket.get('assigned_to')
            if assigned:
                team_performance[assigned] = team_performance.get(assigned, 0) + 1
        
        total_claims = len(all_tickets_db)
        
        # Calculate percentages
        if total_claims > 0:
            approved_percent = (approved_claims / total_claims) * 100
            declined_percent = (declined_claims / total_claims) * 100
            referred_percent = (referred_claims / total_claims) * 100
                
    except Exception as e:
        logger.error(f"Error calculating dashboard metrics: {e}")
    
    return render_template('dashboard.html',
                          tickets=tickets,
                          all_tickets=tickets,
                          current_member=current_member,
                          current_user=current_member.get('name') or session.get('member_name') or 'User',
                          current_user_role=current_member.get('role') or session.get('member_role') or 'User',
                          members=members,
                          technicians=technicians,
                          ticket_statuses=ticket_statuses,
                          status_counts=status_counts,
                          total_tickets=total_claims,
                          overdue_tickets=overdue_tickets,
                          open_1_3_days=open_1_3_days,
                          open_today=open_today,
                          unread_tickets=unread_tickets,
                          avg_resolution_time=avg_resolution_time,
                          total_claims=total_claims,
                          approved_claims=approved_claims,
                          declined_claims=declined_claims,
                          referred_claims=referred_claims,
                          approved_percent=approved_percent,
                          declined_percent=declined_percent,
                          referred_percent=referred_percent,
                          rejection_reasons=rejection_reasons,
                          team_performance=team_performance,
                          pagination=None)


@main_bp.route('/ticket/<ticket_id>')
def ticket_detail(ticket_id):
    """View single ticket details."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member:
        return redirect(url_for('auth.login'))
    
    from database import get_db
    db = get_db()
    
    ticket = db.get_ticket_by_id(ticket_id)
    if not ticket:
        flash('Ticket not found', 'error')
        return redirect(url_for('main.index'))
    
    replies = db.get_replies_by_ticket(ticket_id)
    members = db.get_all_members()
    technicians = list(db.technicians.find({"is_active": True}))
    ticket_statuses = list(db.ticket_statuses.find({"is_active": True}).sort("order", 1))
    
    return render_template('ticket_detail.html',
                          ticket=ticket,
                          replies=replies,
                          current_member=current_member,
                          current_user=current_member.get('name') or 'User',
                          current_user_role=current_member.get('role') or 'User',
                          members=members,
                          technicians=technicians,
                          ticket_statuses=ticket_statuses)


@main_bp.route('/create-ticket', methods=['GET', 'POST'])
def create_ticket():
    """Create a new ticket."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member:
        return redirect(url_for('auth.login'))
    
    from database import get_db
    import uuid
    db = get_db()
    
    if request.method == 'POST':
        ticket_data = {
            'ticket_id': 'M' + str(uuid.uuid4())[:5].upper(),
            'subject': request.form.get('subject', ''),
            'body': request.form.get('body', ''),
            'name': request.form.get('name', current_member.get('name', '')),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'status': 'New',
            'priority': request.form.get('priority', 'Medium'),
            'created_at': datetime.now(),
            'creation_method': 'manual'
        }
        
        try:
            db.create_ticket(ticket_data)
            flash('Ticket created successfully!', 'success')
            return redirect(url_for('main.ticket_detail', ticket_id=ticket_data['ticket_id']))
        except Exception as e:
            flash(f'Error creating ticket: {e}', 'error')
    
    technicians = list(db.technicians.find({"is_active": True}))
    
    return render_template('create_ticket.html',
                          current_member=current_member,
                          current_user=current_member.get('name') or 'User',
                          current_user_role=current_member.get('role') or 'User',
                          technicians=technicians)


@main_bp.route('/status')
def status_page():
    """Status overview page."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member:
        return redirect(url_for('auth.login'))
    
    from database import get_db
    db = get_db()
    
    ticket_statuses = list(db.ticket_statuses.find({"is_active": True}).sort("order", 1))
    
    # Calculate all stats
    all_tickets = list(db.tickets.find({}))
    
    status_counts = {}
    priority_counts = {'Urgent': 0, 'Fast': 0, 'High': 0, 'Medium': 0, 'Low': 0}
    
    active_tickets = 0
    waiting_tickets = 0
    resolved_today = 0
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for ticket in all_tickets:
        # Status counts
        status = ticket.get('status', 'Open')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Priority counts
        priority = ticket.get('priority', 'Medium')
        if priority in priority_counts:
            priority_counts[priority] += 1
            
        # Active tickets (not closed/resolved)
        if status not in ['Closed', 'Resolved']:
            active_tickets += 1
            
        # Waiting tickets
        if 'Waiting' in status:
            waiting_tickets += 1
            
        # Resolved today
        if status == 'Resolved':
            # Check updated_at if available, otherwise estimate or check created_at if seemingly new
            updated_at = ticket.get('updated_at')
            if updated_at and isinstance(updated_at, datetime) and updated_at >= today_start:
                resolved_today += 1
    
    # Get recent tickets for the table (limited to 20 for simplicity on this view)
    recent_tickets = db.get_tickets_with_assignments(page=1, per_page=20)
    
    return render_template('status.html',
                          current_member=current_member,
                          current_user=current_member.get('name') or session.get('member_name') or 'User',
                          current_user_role=current_member.get('role') or session.get('member_role') or 'User',
                          ticket_statuses=ticket_statuses,
                          status_counts=status_counts,
                          priority_counts=priority_counts,
                          total_tickets=len(all_tickets),
                          active_tickets=active_tickets,
                          waiting_tickets=waiting_tickets,
                          resolved_today=resolved_today,
                          recent_tickets=recent_tickets,
                          pagination=None) # Start without pagination to avoid complexity, template handles null pagination


@main_bp.route('/members')
def members_page():
    """Members management page."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member or current_member.get('role') != 'Administrator':
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    from database import get_db
    db = get_db()
    
    members = db.get_all_members()
    
    return render_template('members.html',
                          current_member=current_member,
                          current_user=current_member.get('name') or session.get('member_name') or 'User',
                          current_user_role=current_member.get('role') or session.get('member_role') or 'User',
                          members=members)


@main_bp.route('/technicians')
def technicians_page():
    """Technicians management page."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member or current_member.get('role') != 'Administrator':
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    from database import get_db
    from flask import session
    db = get_db()
    
    technicians = list(db.technicians.find())
    
    # Use session data as fallback for navigation display
    current_user = current_member.get('name') or session.get('member_name') or 'User'
    current_user_role = current_member.get('role') or session.get('member_role') or 'User'
    
    # DEBUG: Log values being passed to template
    print(f"🔍 TECHNICIANS DEBUG: current_member={current_member}")
    # Use fixed template with hardcoded navigation for reliability
    return render_template('technicians_fixed.html',
                          current_member=current_member,
                          technicians=technicians)


@main_bp.route('/admin')
def admin_panel():
    """Admin panel page."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member or current_member.get('role') != 'Administrator':
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    from database import get_db
    db = get_db()
    
    members = db.get_all_members()
    technicians_raw = list(db.technicians.find())
    ticket_statuses_raw = list(db.ticket_statuses.find().sort("order", 1))
    roles_raw = list(db.roles.find())
    
    # Convert ObjectId to string for JSON serialization in templates (preserve datetime for strftime)
    def serialize_doc(doc):
        """Convert MongoDB document ObjectId fields to strings. Preserves datetime for template use."""
        if doc is None:
            return None
        serialized = {}
        for key, value in doc.items():
            if hasattr(value, '__str__') and type(value).__name__ == 'ObjectId':
                serialized[key] = str(value)
            elif isinstance(value, dict):
                serialized[key] = serialize_doc(value)
            elif isinstance(value, list):
                serialized[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value
        return serialized
    
    technicians = [serialize_doc(t) for t in technicians_raw]
    ticket_statuses = [serialize_doc(s) for s in ticket_statuses_raw]
    roles = [serialize_doc(r) for r in roles_raw]
    members = [serialize_doc(m) for m in members]
    
    # Calculate stats for admin template
    all_tickets = list(db.tickets.find({}))
    
    # Get recent tickets with formatting for the list
    tickets = db.get_tickets_with_assignments(page=1, per_page=50)
    
    priorities = {'Urgent': 0, 'Fast': 0, 'High': 0, 'Medium': 0, 'Low': 0}
    classifications = {'Technical Issue': 0, 'Payment': 0, 'Support': 0, 'Warranty Claim': 0, 'Spam': 0, 'Account': 0}
    status_counts = {}
    
    open_tickets = 0
    resolved_tickets = 0
    active_tickets = 0
    
    for ticket in all_tickets:
        priority = ticket.get('priority', 'Medium')
        if priority in priorities:
            priorities[priority] += 1
            
        classification = ticket.get('classification', 'General')
        if classification in classifications:
            classifications[classification] += 1
            
        status = ticket.get('status', 'Open')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count ticket states
        if status in ['Resolved', 'Closed']:
            resolved_tickets += 1
        else:
            active_tickets += 1
            if status in ['Open', 'New', 'Reopened']:
                open_tickets += 1
    
    # Use session data as fallback for navigation display
    from flask import session
    current_user = current_member.get('name') or session.get('member_name') or 'User'
    current_user_role = current_member.get('role') or session.get('member_role') or 'User'
    
    return render_template('admin.html',
                          current_member=current_member,
                          current_user=current_user,
                          current_user_role=current_user_role,
                          members=members,
                          technicians=technicians,
                          ticket_statuses=ticket_statuses,
                          roles=roles,
                          priorities=priorities,
                          classifications=classifications,
                          status_counts=status_counts,
                          tickets=tickets,
                          total_tickets=len(all_tickets),
                          open_tickets=open_tickets,
                          resolved_tickets=resolved_tickets,
                          active_tickets=active_tickets)


@main_bp.route('/tech-director-dashboard')
def tech_director_dashboard():
    """Technical Director dashboard."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
    
    current_member = safe_member_lookup()
    if not current_member:
        return redirect(url_for('auth.login'))
    
    from database import get_db
    db = get_db()
    
    referred_tickets = list(db.tickets.find({
        "status": {"$regex": "Referred", "$options": "i"}
    }).sort("created_at", -1))
    
    return render_template('tech_director_dashboard.html',
                          current_member=current_member,
                          current_user=current_member.get('name') or session.get('member_name') or 'User',
                          current_user_role=current_member.get('role') or session.get('member_role') or 'User',
                          referred_tickets=referred_tickets)


@main_bp.route('/portal')
def portal():
    """Portal page."""
    return render_template('portal.html')
