import logging
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from service.schedule import formal_scheduler_api, display_schedule
from service.db import (
    read_teachers, read_staff, read_rooms,
    get_all_schedules, get_schedule_assignments,
    save_schedule_to_db, delete_schedule, rename_schedule
)

logger = logging.getLogger(__name__)

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('/api/schedule', methods=['POST'])
@login_required
def generate_schedule():
    """Generate the invigilation schedule based on selected exam dates, rooms, and preferences."""
    try:
        data = request.json or {}
        exam_dates = data.get('exam_dates', [])
        
        if not exam_dates or not isinstance(exam_dates, list):
            logger.warning('No exam dates provided')
            return jsonify({'success': False, 'error': 'No valid exam dates provided'}), 400
        
        # Filter out empty strings
        exam_dates = [date.strip() for date in exam_dates if date.strip()]
        if not exam_dates:
            logger.warning('No valid exam dates after filtering')
            return jsonify({'success': False, 'error': 'No valid exam dates found'}), 400
        
        logger.info(f'Schedule generation started with {len(exam_dates)} dates: {exam_dates}')
        shifts = ["Morning", "Afternoon"]
        
        teachers = read_teachers(current_user.id)
        staff = read_staff(current_user.id)
        rooms = read_rooms(current_user.id)
        
        logger.info(f'Loaded {len(teachers)} teachers, {len(staff)} staff, {len(rooms)} rooms')
        
        if not teachers:
            return jsonify({'success': False, 'error': 'No teachers registered'}), 400
        if not staff:
            return jsonify({'success': False, 'error': 'No staff registered'}), 400
        if not rooms:
            return jsonify({'success': False, 'error': 'No rooms registered'}), 400
        
        preferences = data.get('preferences', [])
        if not isinstance(preferences, list):
            preferences = []
        
        two_shift_preferences = data.get('two_shift_preferences', [])
        if not isinstance(two_shift_preferences, list):
            two_shift_preferences = []
        
        req_fac = int(data.get('req_fac', 2))
        req_stf = int(data.get('req_stf', 1))
        
        results, status = formal_scheduler_api(
            teachers, staff, rooms, exam_dates,
            preferences=preferences,
            two_shift_preferences=two_shift_preferences,
            req_fac=req_fac,
            req_stf=req_stf
        )
        
        formatted_results = []
        for result in results:
            date_idx = result.get('date', 0)
            shift_idx = result.get('shift', 0)
            room_idx = result.get('room', 0)
            
            fac_names = [teachers[i] if 0 <= i < len(teachers) else 'N/A' for i in result.get('faculties', [])]
            stf_names = [staff[i] if 0 <= i < len(staff) else 'N/A' for i in result.get('staffs', [])]
            
            formatted_results.append({
                'date': exam_dates[date_idx] if date_idx < len(exam_dates) else f'Date {date_idx + 1}',
                'shift': shifts[shift_idx] if shift_idx < len(shifts) else f'Shift {shift_idx + 1}',
                'room': rooms[room_idx] if room_idx < len(rooms) else f'Room {room_idx + 1}',
                'faculties': fac_names,
                'staffs': stf_names
            })
        
        version_name = data.get('version_name')
        try:
            csv_path = display_schedule(results, teachers, staff, rooms, exam_dates, version_name=version_name)
            logger.info(f'CSV successfully saved to: {csv_path}')
        except Exception as e:
            logger.error(f'Error generating CSV: {str(e)}')
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'status': status
        })
    
    except Exception as e:
        logger.error(f'Schedule generation failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 400

@schedule_bp.route('/api/emergency_reschedule', methods=['POST'])
@login_required
def emergency_reschedule():
    """Takes an absentee and emergency date, loads prior assignments, and regenerates balanced schedule."""
    try:
        data = request.json or {}
        person = data.get('person')
        em_date = data.get('emergency_date')
        schedule_id = data.get('schedule_id')
        
        if not person or not em_date or not schedule_id:
            return jsonify({'success': False, 'error': 'Person, emergency date, and schedule ID required.'}), 400
            
        locked_assignments = get_schedule_assignments(current_user.id, schedule_id)
        if not locked_assignments:
            return jsonify({'success': False, 'error': 'No prior schedule found in database for that ID.'}), 400
            
        for row in locked_assignments:
            if hasattr(row['exam_date'], 'strftime'):
                row['exam_date'] = row['exam_date'].strftime('%Y-%m-%d')

        dates_ordered = []
        for row in locked_assignments:
            if row['exam_date'] not in dates_ordered:
                dates_ordered.append(row['exam_date'])
        
        req_fac = 2
        req_stf = 1
        for row in locked_assignments:
            role = row['role']
            if role.startswith('Faculty_'):
                try:
                    idx = int(role.split('_')[1])
                    if idx > req_fac:
                        req_fac = idx
                except (ValueError, IndexError):
                    pass
            elif role.startswith('Staff_'):
                try:
                    idx = int(role.split('_')[1])
                    if idx > req_stf:
                        req_stf = idx
                except (ValueError, IndexError):
                    pass
        
        teachers = read_teachers(current_user.id)
        staff = read_staff(current_user.id)
        rooms = read_rooms(current_user.id)
        shifts = ["Morning", "Afternoon"]

        results, status = formal_scheduler_api(
            teachers, staff, rooms, dates_ordered, 
            preferences=None, two_shift_preferences=None,
            locked_assignments=locked_assignments,
            emergency_absence=person,
            emergency_date=em_date,
            req_fac=req_fac,
            req_stf=req_stf
        )
        
        formatted_results = []
        for result in results:
            date_idx = result.get('date', 0)
            shift_idx = result.get('shift', 0)
            room_idx = result.get('room', 0)
            
            fac_names = [teachers[i] if 0 <= i < len(teachers) else 'N/A' for i in result.get('faculties', [])]
            stf_names = [staff[i] if 0 <= i < len(staff) else 'N/A' for i in result.get('staffs', [])]
            
            formatted_results.append({
                'date': dates_ordered[date_idx],
                'shift': shifts[shift_idx],
                'room': rooms[room_idx],
                'faculties': fac_names,
                'staffs': stf_names
            })
            
        display_schedule(results, teachers, staff, rooms, dates_ordered, version_name=f"EmResched_{person}")
        return jsonify({'success': True, 'results': formatted_results, 'status': status})
    except Exception as e:
        logger.error(f'Emergency reschedule failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/routines', methods=['GET'])
@login_required
def get_routines():
    """Retrieve saved schedules/routines metadata for current user."""
    try:
        routines = get_all_schedules(current_user.id)
        plain_routines = []
        for row in routines:
            if 'created_at' in row and row['created_at']:
                ca = row['created_at']
                if hasattr(ca, 'strftime'):
                    row['created_at'] = ca.strftime('%Y-%m-%dT%H:%M:%S')
            plain_routines.append(row)
        return jsonify({'success': True, 'routines': plain_routines})
    except Exception as e:
        logger.error(f'Failed to get routines: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/routine/<int:schedule_id>', methods=['GET'])
@login_required
def get_routine(schedule_id):
    """Retrieve a specific saved routine with all slot assignments."""
    try:
        assignments = get_schedule_assignments(current_user.id, schedule_id)
        if not assignments:
            return jsonify({'success': False, 'error': 'Routine not found'}), 404
        
        for a in assignments:
            if hasattr(a['exam_date'], 'strftime'):
                a['exam_date'] = a['exam_date'].strftime('%Y-%m-%d')

        unique_dates = sorted(list(set([row['exam_date'] for row in assignments])))
        formatted_results = []
        
        grouped = {}
        for a in assignments:
            key = (a['exam_date'], a['shift_name'], a['room_name'])
            if key not in grouped:
                grouped[key] = {'faculties': {}, 'staffs': {}}
            
            role = a['role']
            if role.startswith('Faculty_'):
                try:
                    idx = int(role.split('_')[1]) - 1
                    grouped[key]['faculties'][idx] = a['person_name']
                except (ValueError, IndexError):
                    pass
            elif role.startswith('Staff_') or role == 'Staff':
                try:
                    idx = int(role.split('_')[1]) - 1 if '_' in role and role != 'Staff' else 0
                    grouped[key]['staffs'][idx] = a['person_name']
                except (ValueError, IndexError):
                    grouped[key]['staffs'][0] = a['person_name']
                
        for (date_str, shift_name, room_name), roles in grouped.items():
            fac_list = [roles['faculties'].get(i, '---') for i in range(max(roles['faculties'].keys(), default=-1) + 1)]
            stf_list = [roles['staffs'].get(i, '---') for i in range(max(roles['staffs'].keys(), default=-1) + 1)]
            formatted_results.append({
                'date': date_str,
                'shift': shift_name,
                'room': room_name,
                'faculties': fac_list,
                'staffs': stf_list
            })
            
        return jsonify({'success': True, 'results': formatted_results, 'dates': unique_dates})
    except Exception as e:
        logger.error(f'Failed to get routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/save_routine', methods=['POST'])
@login_required
def save_routine_api():
    """Save the currently generated schedule under a routine name."""
    try:
        data = request.json or {}
        results = data.get('results')
        version_name = data.get('version_name')
        
        if not results:
            return jsonify({'success': False, 'error': 'No schedule results to save'}), 400
        if not version_name:
            return jsonify({'success': False, 'error': 'Routine name is required'}), 400
            
        db_results = []
        for r in results:
            db_results.append({
                "Date": r.get('date'),
                "Shift": r.get('shift'),
                "Room": r.get('room'),
                "faculties": r.get('faculties', []),
                "staffs": r.get('staffs', [])
            })
            
        schedule_id = save_schedule_to_db(current_user.id, version_name, db_results)
        return jsonify({'success': True, 'message': 'Routine saved successfully', 'id': schedule_id})
    except Exception as e:
        logger.error(f'Failed to save routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/routine/<int:schedule_id>', methods=['DELETE'])
@login_required
def delete_routine_api(schedule_id):
    """Delete a saved routine."""
    try:
        if delete_schedule(current_user.id, schedule_id):
            return jsonify({'success': True, 'message': 'Routine deleted successfully'})
        return jsonify({'success': False, 'error': 'Failed to delete routine'}), 400
    except Exception as e:
        logger.error(f'Failed to delete routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/routine/<int:schedule_id>', methods=['PUT'])
@login_required
def rename_routine_api(schedule_id):
    """Rename a saved routine."""
    try:
        data = request.json or {}
        new_name = data.get('name')
        if not new_name:
            return jsonify({'success': False, 'error': 'New name is required'}), 400
            
        if rename_schedule(current_user.id, schedule_id, new_name):
            return jsonify({'success': True, 'message': 'Routine renamed successfully'})
        return jsonify({'success': False, 'error': 'Failed to rename routine'}), 400
    except Exception as e:
        logger.error(f'Failed to rename routine: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500
