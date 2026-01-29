"""
Admin Routes

Handles administrative API operations including:
- Member management (CRUD)
- Technician management
- Role and status configuration
- System settings

Author: AutoAssistGroup Development Team
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, session
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId

from middleware.session_manager import is_authenticated, is_admin, safe_member_lookup

logger = logging.getLogger(__name__)

# Create blueprint - Note: Page routes are in main_routes.py
# This blueprint only handles API endpoints
admin_bp = Blueprint('admin', __name__)


# ============ MEMBER MANAGEMENT API ============


@admin_bp.route('/api/members', methods=['GET', 'POST'])
def manage_members():
    """GET all members or POST to create new member."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    from database import get_db
    db = get_db()
    
    if request.method == 'GET':
        members = db.get_all_members()
        return jsonify({
            'success': True,
            'members': [_serialize_member(m) for m in members]
        })
    
    # POST - Create new member
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    required_fields = ['name', 'user_id', 'password', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    try:
        member_data = {
            'name': data['name'],
            'user_id': data['user_id'],
            'password_hash': generate_password_hash(data['password']),
            'role': data['role'],
            'email': data.get('email', ''),
            'gender': data.get('gender', 'other'),
            'department': data.get('department', ''),
            'is_active': True,
            'created_at': datetime.now()
        }
        
        member_id = db.create_member(member_data)
        
        logger.info(f"Member created: {data['name']} by {session.get('member_name')}")
        
        return jsonify({
            'success': True,
            'message': 'Member created successfully',
            'member_id': str(member_id)
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating member: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/members/<member_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_member(member_id):
    """GET, UPDATE, or DELETE a specific member."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    from database import get_db
    db = get_db()
    
    if request.method == 'GET':
        member = db.get_member_by_id(member_id)
        if not member:
            return jsonify({'success': False, 'error': 'Member not found'}), 404
        return jsonify({'success': True, 'member': _serialize_member(member)})
    
    # PUT/DELETE require admin
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    if request.method == 'PUT':
        data = request.get_json()
        update_data = {
            'updated_at': datetime.now()
        }
        
        # Only update provided fields
        for field in ['name', 'role', 'email', 'department', 'is_active']:
            if field in data:
                update_data[field] = data[field]
        
        # Handle password update separately
        if data.get('password'):
            update_data['password_hash'] = generate_password_hash(data['password'])
        
        db.members.update_one(
            {'_id': ObjectId(member_id)},
            {'$set': update_data}
        )
        
        logger.info(f"Member {member_id} updated by {session.get('member_name')}")
        
        return jsonify({'success': True, 'message': 'Member updated'})
    
    if request.method == 'DELETE':
        # Soft delete - mark as inactive
        db.members.update_one(
            {'_id': ObjectId(member_id)},
            {'$set': {'is_active': False, 'deleted_at': datetime.now()}}
        )
        
        logger.info(f"Member {member_id} deactivated by {session.get('member_name')}")
        
        return jsonify({'success': True, 'message': 'Member deactivated'})


# ============ TECHNICIAN MANAGEMENT ============

@admin_bp.route('/technicians', methods=['GET'])
def technicians_management():
    """Technicians management page."""
    if not is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    current_member = safe_member_lookup()
    if not current_member:
        return jsonify({'error': 'Member not found'}), 404
    
    from database import get_db
    db = get_db()
    technicians = db.get_all_technicians()
    
    return render_template('technicians.html',
                          technicians=technicians,
                          current_member=current_member,
                          current_user=current_member.get('name'),
                          current_user_role=current_member.get('role'))


@admin_bp.route('/api/technicians', methods=['GET', 'POST'])
def manage_technicians():
    """GET all technicians or POST to create new technician."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    from database import get_db
    db = get_db()
    
    if request.method == 'GET':
        technicians = db.get_all_technicians()
        return jsonify({
            'success': True,
            'technicians': [_serialize_technician(t) for t in technicians]
        })
    
    # POST - Create new technician (Admin only)
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    try:
        technician_data = {
            'name': data['name'],
            'role': data.get('role', 'Technician'),
            'email': data.get('email', ''),
            'is_active': True,
            'created_at': datetime.now()
        }
        
        technician_id = db.create_technician(technician_data)
        
        logger.info(f"Technician created: {data['name']} by {session.get('member_name')}")
        
        return jsonify({
            'success': True,
            'message': 'Technician created successfully',
            'technician_id': str(technician_id)
        })
        
    except Exception as e:
        logger.error(f"Error creating technician: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/technicians/<technician_id>', methods=['PUT', 'DELETE'])
def manage_technician(technician_id):
    """UPDATE or DELETE a specific technician."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    from database import get_db
    db = get_db()
    
    if request.method == 'PUT':
        data = request.get_json()
        update_data = {'updated_at': datetime.now()}
        
        for field in ['name', 'role', 'email', 'is_active']:
            if field in data:
                update_data[field] = data[field]
        
        db.update_technician(technician_id, update_data)
        
        logger.info(f"Technician {technician_id} updated by {session.get('member_name')}")
        
        return jsonify({'success': True, 'message': 'Technician updated'})
    
    if request.method == 'DELETE':
        db.deactivate_technician(technician_id)
        
        logger.info(f"Technician {technician_id} deactivated by {session.get('member_name')}")
        
        return jsonify({'success': True, 'message': 'Technician deactivated'})


# ============ ROLES & STATUSES ============

@admin_bp.route('/api/roles', methods=['GET', 'POST'])
def handle_roles():
    """GET all roles or POST to create new role."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    from database import get_db
    db = get_db()
    
    if request.method == 'GET':
        roles = db.get_all_roles()
        return jsonify({
            'success': True,
            'roles': [_serialize_role(r) for r in roles]
        })
    
    # POST - Admin only
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Role name required'}), 400
    
    role_id = db.create_role(data)
    return jsonify({'success': True, 'role_id': str(role_id)})


@admin_bp.route('/api/statuses', methods=['GET', 'POST'])
def manage_statuses():
    """GET all statuses or POST to create new status."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    from database import get_db
    db = get_db()
    
    if request.method == 'GET':
        statuses = db.get_all_ticket_statuses()
        return jsonify({
            'success': True,
            'statuses': [{'_id': str(s.get('_id')), **{k: v for k, v in s.items() if k != '_id'}} for s in statuses]
        })
    
    # POST - Admin only
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.get_json()
    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Status name required'}), 400
    
    status_id = db.create_ticket_status(data)
    return jsonify({'success': True, 'status_id': str(status_id)})



# ============ SYSTEM SETTINGS API ============

@admin_bp.route('/api/system-settings', methods=['GET', 'POST'])
def manage_system_settings():
    """GET current settings or POST to update them."""
    if not is_authenticated():
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    # Check for admin access for updates
    if request.method == 'POST' and not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
    from database import get_db
    db = get_db()
    
    if request.method == 'GET':
        settings = db.get_system_settings()
        return jsonify({
            'success': True,
            'settings': settings
        })
    
    # POST - Update settings
    data = request.get_json()
    success = db.update_system_settings(data)
    
    return jsonify({'success': success})


# ============ HELPER FUNCTIONS ============

def _serialize_member(member):
    """Serialize member for JSON response."""
    if not member:
        return None
    return {
        '_id': str(member.get('_id')),
        'name': member.get('name'),
        'user_id': member.get('user_id'),
        'role': member.get('role'),
        'email': member.get('email'),
        'department': member.get('department'),
        'is_active': member.get('is_active', True),
        'created_at': member.get('created_at').isoformat() if member.get('created_at') else None
    }


def _serialize_technician(tech):
    """Serialize technician for JSON response."""
    if not tech:
        return None
    return {
        '_id': str(tech.get('_id')),
        'name': tech.get('name'),
        'role': tech.get('role'),
        'email': tech.get('email'),
        'is_active': tech.get('is_active', True),
        'created_at': tech.get('created_at').isoformat() if tech.get('created_at') else None
    }


def _serialize_role(role):
    """Serialize role for JSON response."""
    if not role:
        return None
    return {
        '_id': str(role.get('_id')),
        'name': role.get('name'),
        'permissions': role.get('permissions', []),
        'description': role.get('description', '')
    }
