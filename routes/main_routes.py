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

import uuid
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId



@main_bp.route('/')
def home():
    """Root route - redirects to portal."""
    return redirect(url_for('main.portal'))


@main_bp.route('/tickets')
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
    
    # Optimized Stats Loading
    ticket_stats = db.get_ticket_stats()
    
    # Extract stats from optimized result
    priorities = ticket_stats.get('priorities', {'Urgent': 0, 'Fast': 0, 'High': 0, 'Medium': 0, 'Low': 0})
    classifications = ticket_stats.get('classifications', {})
    status_counts = ticket_stats.get('status_counts', {})
    
    # Calculate derived metrics from status counts
    open_tickets = 0
    waiting_tickets = 0
    resolved_tickets = 0
    
    for status, count in status_counts.items():
        if status in ['Open', 'New', 'Reopened']:
            open_tickets += count
        elif 'Waiting' in status:
            waiting_tickets += count
        elif status in ['Resolved', 'Closed']:
            resolved_tickets += count

    # Handling forwarded tickets (still need to check this member-specific logic)
    # Optimization: We can just filter the current view 'tickets' if they are forwarded? 
    # Or keep it simple and just show forwarded if they appear in the paginated list.
    # For the counters in the top bar, we might need a specific query for "My Forwarded Tickets" if that's critical.
    # For now, let's keep forwarded_tickets empty or fetch only assigned to me if strictly needed.
    # Optimizing to NOT fetch all DB tickets just for this.
    forwarded_tickets = [] 
    
    total_tickets = ticket_stats.get('total_tickets', 0)
    
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
                          all_tickets=tickets, # Keep for compatibility, but it's just the page now
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
    
    # Optimized Dashboard Stats (using ticket stats instead of warranty claims)
    ticket_stats = db.get_ticket_stats()
    status_counts = ticket_stats.get('status_counts', {})
    priority_counts = ticket_stats.get('priorities', {})
    total_tickets = ticket_stats.get('total_tickets', 0)
    
    active_tickets = 0
    waiting_tickets = 0
    
    for status, count in status_counts.items():
        if status not in ['Closed', 'Resolved']:
            active_tickets += count
        if 'Waiting' in status:
            waiting_tickets += count
            
    # "Resolved Today" requires a specific date query or aggregation we can add later.
    # For now, let's keep it 0 or add a lightweight query if needed. 
    resolved_today = 0
    
    return render_template('dashboard.html',
                          tickets=tickets,
                          recent_tickets=tickets, # Reuse the tickets list for the recent table
                          current_member=current_member,
                          current_user=current_member.get('name') or session.get('member_name') or 'User',
                          current_user_role=current_member.get('role') or session.get('member_role') or 'User',
                          members=members,
                          technicians=technicians,
                          ticket_statuses=ticket_statuses,
                          status_counts=status_counts,
                          priority_counts=priority_counts,
                          total_tickets=total_tickets,
                          active_tickets=active_tickets,
                          waiting_tickets=waiting_tickets,
                          resolved_today=resolved_today,
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


@main_bp.route('/members/add', methods=['POST'])
def add_member():
    """Add a new team member."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
        
    current_member = safe_member_lookup()
    if not current_member or current_member.get('role') != 'Administrator':
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
        
    from database import get_db
    db = get_db()
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    gender = request.form.get('gender')
    
    if not name or not email or not password or not role:
        flash('All required fields must be filled', 'error')
        return redirect(url_for('main.members_page'))
        
    try:
        # Generate user_id from email prefix or name if email is malformed
        user_id = email.split('@')[0].lower() if '@' in email else name.lower().replace(' ', '')
        
        member_data = {
            'name': name,
            'email': email,
            'user_id': user_id,
            'password_hash': generate_password_hash(password),
            'role': role,
            'gender': gender,
            'is_active': True,
            'created_at': datetime.now()
        }
        
        db.create_member(member_data)
        flash(f'Member {name} added successfully!', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Error adding member: {e}', 'error')
        
    return redirect(url_for('main.members_page'))


@main_bp.route('/members/edit', methods=['POST'])
def edit_member():
    """Edit an existing team member."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
        
    current_member = safe_member_lookup()
    if not current_member or current_member.get('role') != 'Administrator':
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
        
    from database import get_db
    db = get_db()
    
    member_id = request.form.get('member_id')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    gender = request.form.get('gender')
    
    if not member_id:
        flash('Member ID is missing', 'error')
        return redirect(url_for('main.members_page'))
        
    try:
        update_data = {
            'name': name,
            'email': email,
            'role': role,
            'gender': gender,
            'updated_at': datetime.now()
        }
        
        # Only update password if provided
        if password:
            update_data['password_hash'] = generate_password_hash(password)
            
        db.members.update_one(
            {'_id': ObjectId(member_id)},
            {'$set': update_data}
        )
        flash(f'Member {name} updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating member: {e}', 'error')
        
    return redirect(url_for('main.members_page'))


@main_bp.route('/members/delete/<member_id>', methods=['POST'])
def delete_member(member_id):
    """Delete (deactivate) a team member."""
    if not is_authenticated():
        return redirect(url_for('auth.login'))
        
    current_member = safe_member_lookup()
    if not current_member or current_member.get('role') != 'Administrator':
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
        
    from database import get_db
    db = get_db()
    
    try:
        # Check if trying to delete self or default admin
        member = db.get_member_by_id(member_id)
        if member:
            if member.get('email') == 'admin@autoassist.com':
                flash('Cannot delete protected admin account', 'error')
            elif str(member.get('_id')) == str(current_member.get('_id')):
                flash('Cannot delete your own account', 'error')
            else:
                db.members.update_one(
                    {'_id': ObjectId(member_id)},
                    {'$set': {'is_active': False, 'deleted_at': datetime.now()}}
                )
                flash('Member deactivated successfully', 'success')
        else:
            flash('Member not found', 'error')
    except Exception as e:
        flash(f'Error deleting member: {e}', 'error')
        
    return redirect(url_for('main.members_page'))


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
    # Use standard template
    return render_template('technicians.html',
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
    
    # Optimized Admin Stats
    ticket_stats = db.get_ticket_stats()
    
    priorities = ticket_stats.get('priorities', {'Urgent': 0, 'Fast': 0, 'High': 0, 'Medium': 0, 'Low': 0})
    classifications = ticket_stats.get('classifications', {})
    status_counts = ticket_stats.get('status_counts', {})
    
    open_tickets = 0
    resolved_tickets = 0
    active_tickets = 0
    waiting_tickets = 0
    
    # Fetch recent tickets for the table
    tickets = db.get_tickets_with_assignments(page=1, per_page=50)

    for status, count in status_counts.items():
        if status in ['Resolved', 'Closed']:
            resolved_tickets += count
        else:
            active_tickets += count
            if status in ['Open', 'New', 'Reopened']:
                open_tickets += count
            if 'Waiting' in status:
                waiting_tickets += count
    
    total_tickets = ticket_stats.get('total_tickets', 0)
    
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
                          total_tickets=total_tickets,
                          open_tickets=open_tickets,
                          resolved_tickets=resolved_tickets,
                          active_tickets=active_tickets,
                          waiting_tickets=waiting_tickets)


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
