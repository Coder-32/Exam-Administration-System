import os
import zipfile
import pandas as pd
from io import BytesIO
try:
    from config import Config
except ImportError:
    from CONFIG import Config

def determine_personnel_limits(results):
    """Determine dynamic maximum faculty and staff counts across all schedule results."""
    max_fac = max(
        (len(r.get('faculties', r.get('faculty1') and [r['faculty1'], r.get('faculty2', '')] or [])) for r in results),
        default=2
    )
    max_stf = max(
        (len(r.get('staffs', r.get('staff') and [r['staff']] or [])) for r in results),
        default=1
    )
    if max_fac <= 0:
        max_fac = 2
    if max_stf <= 0:
        max_stf = 1
    return max_fac, max_stf

def get_faculty_at(row, i):
    """Retrieve faculty name at index i from a schedule row dictionary."""
    facs = row.get('faculties')
    if facs is not None:
        return facs[i] if i < len(facs) else '---'
    if i == 0:
        return row.get('faculty1', '---')
    if i == 1:
        return row.get('faculty2', '---')
    return '---'

def get_staff_at(row, i):
    """Retrieve staff name at index i from a schedule row dictionary."""
    stfs = row.get('staffs')
    if stfs is not None:
        return stfs[i] if i < len(stfs) else '---'
    if i == 0:
        return row.get('staff', '---')
    return '---'

def build_grouped_dataframe(results, csv_type='main'):
    """
    Build a pandas DataFrame formatted for the specified schedule export view.
    
    Args:
        results: List of schedule assignment dictionaries.
        csv_type: 'main', 'teacher', 'staff', or 'room'.
        
    Returns:
        tuple: (pd.DataFrame, filename)
    """
    max_fac, max_stf = determine_personnel_limits(results)
    fac_col_names = [f'Faculty {i+1}' for i in range(max_fac)]
    stf_col_names = [f'Staff {i+1}' for i in range(max_stf)]

    if csv_type == 'teacher':
        teacher_records = []
        for row in results:
            facs = row.get('faculties') or [row.get('faculty1'), row.get('faculty2')]
            for i, name in enumerate(facs):
                if name and name not in ('N/A', '---', None, ''):
                    teacher_records.append({
                        'Teacher': name,
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room'],
                        'Role': f'Faculty {i+1}'
                    })
        if teacher_records:
            df = pd.DataFrame(teacher_records).sort_values(['Teacher', 'Date', 'Shift']).reset_index(drop=True)
        else:
            df = pd.DataFrame(columns=['Teacher', 'Date', 'Shift', 'Room', 'Role'])
        filename = Config.TEACHER_SCHEDULE_CSV

    elif csv_type == 'staff':
        staff_records = []
        for row in results:
            stfs = row.get('staffs') or [row.get('staff')]
            for i, name in enumerate(stfs):
                if name and name not in ('N/A', '---', None, ''):
                    rec = {
                        'Staff': name,
                        'Date': row['date'],
                        'Shift': row['shift'],
                        'Room': row['room']
                    }
                    for fi in range(max_fac):
                        rec[fac_col_names[fi]] = get_faculty_at(row, fi)
                    staff_records.append(rec)
        if staff_records:
            df = pd.DataFrame(staff_records).sort_values(['Staff', 'Date', 'Shift']).reset_index(drop=True)
        else:
            df = pd.DataFrame(columns=['Staff', 'Date', 'Shift', 'Room'] + fac_col_names)
        filename = Config.STAFF_SCHEDULE_CSV

    elif csv_type == 'room':
        room_records = []
        for row in results:
            rec = {
                'Date': row['date'],
                'Room': row['room'],
                'Shift': row['shift']
            }
            for i in range(max_fac):
                rec[fac_col_names[i]] = get_faculty_at(row, i)
            for i in range(max_stf):
                rec[stf_col_names[i]] = get_staff_at(row, i)
            room_records.append(rec)
        if room_records:
            df = pd.DataFrame(room_records).sort_values(['Room', 'Date', 'Shift']).reset_index(drop=True)
        else:
            df = pd.DataFrame(columns=['Date', 'Room', 'Shift'] + fac_col_names + stf_col_names)
        filename = Config.ROOM_SCHEDULE_CSV

    else:  # 'main'
        main_records = []
        for row in results:
            rec = {
                'Date': row['date'],
                'Shift': row['shift'],
                'Room': row['room']
            }
            for i in range(max_fac):
                rec[fac_col_names[i]] = get_faculty_at(row, i)
            for i in range(max_stf):
                rec[stf_col_names[i]] = get_staff_at(row, i)
            main_records.append(rec)
        df = pd.DataFrame(main_records) if main_records else pd.DataFrame(columns=['Date', 'Shift', 'Room'] + fac_col_names + stf_col_names)
        filename = Config.MAIN_SCHEDULE_CSV

    return df, filename

def generate_schedules_zip(results):
    """
    Generate an in-memory ZIP buffer containing all 4 schedule views (Main, Teacher, Staff, Room).
    
    Args:
        results: List of schedule assignment dictionaries.
        
    Returns:
        BytesIO: In-memory zip file buffer.
    """
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for csv_type in ['main', 'teacher', 'staff', 'room']:
            df, filename = build_grouped_dataframe(results, csv_type)
            zip_file.writestr(filename, df.to_csv(index=False))
            
    zip_buffer.seek(0)
    return zip_buffer
