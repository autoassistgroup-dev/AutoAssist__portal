"""
Authentication Routes

Handles user authentication including:
- Login page and processing
- Logout
- Session management endpoints

Author: AutoAssistGroup Development Team
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash

from middleware.session_manager import (
    init_session, clear_session, refresh_session, 
    check_and_restore_session, is_authenticated
)

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'GET':
        # If already logged in, redirect to dashboard
        if is_authenticated():
            return redirect(url_for('main.dashboard'))
        
        # Get role filter from query parameter
        selected_role = request.args.get('role', '').lower()
            
        # Fetch members for the "Select Account" UI
        members = []
        try:
            from database import get_db
            db = get_db()
            # Get members sorted by role priority
            all_members = db.get_all_members()
            
            # Filter members based on selected role
            if selected_role == 'admin':
                # Show only administrators
                members = [m for m in all_members if 'Admin' in m.get('role', '')]
            elif selected_role == 'tech-director':
                # Show only technical directors
                members = [m for m in all_members if 'Director' in m.get('role', '')]
            elif selected_role == 'user':
                # Show only regular users (not admin or director)
                members = [m for m in all_members if 'Admin' not in m.get('role', '') and 'Director' not in m.get('role', '')]
            else:
                # No filter - show all members sorted by role priority
                def get_rank(m):
                    role = m.get('role', '')
                    if 'Admin' in role: return 0
                    if 'Director' in role: return 1
                    return 2
                members = sorted(all_members, key=get_rank)
                
        except Exception as e:
            logger.warning(f"Could not fetch members for login screen: {e}")
            # FALLBACK FOR OFFLINE/CONNECTION ISSUES
            if selected_role == 'admin':
                members = [{"_id": "admin_dummy", "name": "Admin", "role": "Administrator", "user_id": "admin001"}]
            elif selected_role == 'tech-director':
                members = [{"_id": "marc_dummy", "name": "Marc (Technical Director)", "role": "Technical Director", "user_id": "marc001"}]
            elif selected_role == 'user':
                members = [{"_id": "user_dummy", "name": "User", "role": "User", "user_id": "user001"}]
            else:
                members = [
                    {"_id": "admin_dummy", "name": "Admin", "role": "Administrator", "user_id": "admin001"},
                    {"_id": "marc_dummy", "name": "Marc (Technical Director)", "role": "Technical Director", "user_id": "marc001"}
                ]
            
        return render_template('login.html', members=members, selected_role=selected_role)
    
    # POST - process login
    try:
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')
        
        if not user_id or not password:
            flash('Please enter both User ID and Password', 'error')
            return render_template('login.html')
        
        # Get database connection
        from database import get_db
        db = get_db()
        
        # Find user
        user = db.get_member_by_user_id(user_id)
        
        if not user:
            logger.warning(f"Login attempt with unknown user_id: {user_id}")
            flash('Invalid User ID or Password', 'error')
            return render_template('login.html')
        
        # Verify password
        if not check_password_hash(user.get('password_hash', ''), password):
            logger.warning(f"Failed login attempt for user: {user_id}")
            flash('Invalid User ID or Password', 'error')
            return render_template('login.html')
        
        # Successful login - initialize session
        init_session(user)
        
        logger.info(f"User logged in: {user.get('name')} ({user_id})")
        
        # Redirect based on role
        role = user.get('role', '')
        if role == 'Technical Director':
            return redirect(url_for('main.tech_director_dashboard'))
        else:
            return redirect(url_for('main.index'))
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        flash('An error occurred during login. Please try again.', 'error')
        return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Handle user logout with proper session cleanup."""
    try:
        user_name = session.get('member_name', 'Unknown')
        user_id = session.get('user_id', 'Unknown')
        
        # Clear session
        clear_session()
        
        logger.info(f"User logged out: {user_name} ({user_id})")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Still clear session even if logging fails
        clear_session()
    
    # Redirect to portal page instead of login
    return redirect(url_for('main.portal'))


@auth_bp.route('/api/session/heartbeat', methods=['POST'])
def session_heartbeat():
    """
    Enhanced session heartbeat with better error handling and session validation.
    Called periodically by frontend to keep session alive.
    """
    try:
        if not is_authenticated():
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'No active session'
            }), 401
        
        # Refresh the session
        if refresh_session():
            return jsonify({
                'success': True,
                'authenticated': True,
                'member_id': session.get('member_id'),
                'member_name': session.get('member_name'),
                'refresh_count': session.get('_refresh_count', 0)
            })
        else:
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'Session refresh failed'
            }), 401
    
    except Exception as e:
        logger.error(f"Session heartbeat error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/api/session/refresh', methods=['POST'])
def session_refresh():
    """Proactively refresh the current session to prevent timeouts."""
    try:
        if not is_authenticated():
            # Try to restore session
            if check_and_restore_session():
                return jsonify({
                    'success': True,
                    'restored': True,
                    'message': 'Session restored'
                })
            return jsonify({
                'success': False,
                'message': 'No session to refresh'
            }), 401
        
        # Refresh the session
        refresh_session()
        
        return jsonify({
            'success': True,
            'message': 'Session refreshed',
            'expires_in': '30 days'
        })
    
    except Exception as e:
        logger.error(f"Session refresh error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@auth_bp.route('/api/session/status', methods=['GET'])
def session_status():
    """Check current session status and health."""
    try:
        authenticated = is_authenticated()
        
        return jsonify({
            'success': True,
            'authenticated': authenticated,
            'member_id': session.get('member_id') if authenticated else None,
            'member_name': session.get('member_name') if authenticated else None,
            'member_role': session.get('member_role') if authenticated else None,
            'refresh_count': session.get('_refresh_count', 0),
            'last_refresh': session.get('_last_refresh'),
            'login_time': session.get('_login_time')
        })
    
    except Exception as e:
        logger.error(f"Session status error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
