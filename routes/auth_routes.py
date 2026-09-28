import logging
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from service.db import (
    get_user_by_id, get_user_by_username, create_user, delete_user, update_password
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = get_user_by_username(username)
        if user and check_password_hash(user.password, password):
            login_user(user)
            return jsonify({'success': True, 'message': 'Logged in successfully'})
        return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
    return render_template('login.html')

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return render_template('login.html', message="Logged out successfully")

@auth_bp.route("/register_account", methods=['GET', 'POST'])
def register_account():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if create_user(username, password):
            return jsonify({'success': True, 'message': 'Account created successfully'})
        return jsonify({'success': False, 'error': 'Username already exists'}), 400
    return render_template('register_account.html')

@auth_bp.route("/api/change-password", methods=['POST'])
@login_required
def api_change_password():
    """Change user password after verifying old password"""
    try:
        data = request.json or {}
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({'success': False, 'error': 'Old and new passwords are required'}), 400
            
        user_with_pw = get_user_by_username(current_user.username)
        
        if not user_with_pw or not check_password_hash(user_with_pw.password, old_password):
            return jsonify({'success': False, 'error': 'Incorrect old password'}), 401
            
        if update_password(current_user.id, new_password):
            return jsonify({'success': True, 'message': 'Password updated successfully'})
        return jsonify({'success': False, 'error': 'Failed to update password'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auth_bp.route("/api/delete-account", methods=['POST'])
@login_required
def api_delete_account():
    """Permanently delete user account and all data"""
    try:
        user_id = current_user.id
        if delete_user(user_id):
            logout_user()
            return jsonify({'success': True, 'message': 'Account deleted successfully'})
        return jsonify({'success': False, 'error': 'Failed to delete account'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
