import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from service.db import (
    get_all_data, add_teacher, add_staff, add_room,
    delete_teacher, delete_staff, delete_room,
    delete_all_teachers, delete_all_staff
)
from utils.ocr_utils import extract_personnel_from_pdf

logger = logging.getLogger(__name__)

personnel_bp = Blueprint('personnel', __name__)

@personnel_bp.route('/api/data', methods=['GET'])
@login_required
def api_data():
    """Return teachers, staff, and rooms for client-side preference setup"""
    data = get_all_data(current_user.id)
    return jsonify({'success': True, 'data': data})

@personnel_bp.route("/api/register-teacher", methods=['POST'])
@login_required
def register_teacher():
    """Register a new teacher"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if add_teacher(current_user.id, name):
            return jsonify({'success': True, 'message': f'Teacher {name} added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Teacher already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/register-staff", methods=['POST'])
@login_required
def register_staff():
    """Register a new staff member"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if add_staff(current_user.id, name):
            return jsonify({'success': True, 'message': f'Staff {name} added successfully'})
        else:
            return jsonify({'success': False, 'error': 'Staff already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/delete-teacher", methods=['POST'])
@login_required
def api_delete_teacher():
    """Delete a teacher"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if delete_teacher(current_user.id, name):
            return jsonify({'success': True, 'message': f'Teacher {name} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Teacher not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/delete-staff", methods=['POST'])
@login_required
def api_delete_staff():
    """Delete a staff member"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if delete_staff(current_user.id, name):
            return jsonify({'success': True, 'message': f'Staff {name} deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Staff not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/delete-all-teachers", methods=['POST'])
@login_required
def api_delete_all_teachers():
    """Delete all teachers for current user"""
    try:
        if delete_all_teachers(current_user.id):
            logger.info('All teachers deleted')
            return jsonify({'success': True, 'message': 'All teachers deleted successfully'})
        return jsonify({'success': False, 'error': 'Failed to delete teachers'}), 400
    except Exception as e:
        logger.error(f'Error deleting all teachers: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/delete-all-staff", methods=['POST'])
@login_required
def api_delete_all_staff():
    """Delete all staff for current user"""
    try:
        if delete_all_staff(current_user.id):
            logger.info('All staff deleted')
            return jsonify({'success': True, 'message': 'All staff deleted successfully'})
        return jsonify({'success': False, 'error': 'Failed to delete staff'}), 400
    except Exception as e:
        logger.error(f'Error deleting all staff: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/register-room", methods=['POST'])
@login_required
def register_room():
    """Register a new examination room"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if add_room(current_user.id, name):
            return jsonify({'success': True, 'message': f'Room {name} added successfully'})
        return jsonify({'success': False, 'error': 'Room already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/delete-room", methods=['POST'])
@login_required
def api_delete_room():
    """Delete a room"""
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400
        
        if delete_room(current_user.id, name):
            return jsonify({'success': True, 'message': f'Room {name} deleted successfully'})
        return jsonify({'success': False, 'error': 'Room not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@personnel_bp.route("/api/upload-pdf-list", methods=['POST'])
@login_required
def upload_pdf_list():
    """API to parse a PDF and bulk add teachers or staff members"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        role = request.form.get('role', '').strip()
        use_ocr = request.form.get('use_ocr', 'false').lower() == 'true'
        
        if not file.filename:
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if role not in ['teacher', 'staff']:
            return jsonify({'success': False, 'error': 'Invalid role specified'}), 400

        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Selected file is not a PDF'}), 400

        file_bytes = file.read()
        names, error_msg = extract_personnel_from_pdf(file_bytes, role, use_ocr=use_ocr)
        if error_msg:
            status_code = 500 if 'Tesseract OCR' in error_msg else 400
            return jsonify({'success': False, 'error': error_msg}), status_code

        added_count = 0
        for name in names:
            if role == 'teacher':
                if add_teacher(current_user.id, name):
                    added_count += 1
            elif role == 'staff':
                if add_staff(current_user.id, name):
                    added_count += 1

        return jsonify({
            'success': True,
            'message': f'Successfully parsed PDF and added {added_count} new {role}(s)!'
        })

    except Exception as e:
        logger.error(f'PDF Upload failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400
