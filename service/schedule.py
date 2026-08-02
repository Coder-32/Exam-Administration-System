import os
import sys
import pandas as pd
from datetime import datetime
import logging
import networkx as nx

# Constant filenames for schedule storage (will be overwritten each time)
MAIN_SCHEDULE_CSV = "exam_schedule.csv"
TEACHER_SCHEDULE_CSV = "teacher_schedule.csv"
STAFF_SCHEDULE_CSV = "staff_schedule.csv"
ROOM_SCHEDULE_CSV = "room_schedule.csv"

try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

sys.path.append(os.path.dirname(__file__))
from db import read_teachers, read_staff, read_rooms

def solve_with_ortools(dates, rooms, shifts, faculties, staffData, req_fac=2, req_stf=1, two_shift_preferences=None, locked_assignments=None, emergency_absence=None, emergency_date=None):
    if not ORTOOLS_AVAILABLE:
        return None
        
    model = cp_model.CpModel()
    
    x_fac = {}
    x_stf = {}
    
    # Create variables
    for f_id in faculties:
        for d in dates:
            for s in shifts:
                for r in rooms:
                    x_fac[(f_id, d, s, r)] = model.NewBoolVar(f"F_{f_id}_{d}_{s}_{r}")
                    
    for s_id in staffData:
        for d in dates:
            for s in shifts:
                for r in rooms:
                    x_stf[(s_id, d, s, r)] = model.NewBoolVar(f"S_{s_id}_{d}_{s}_{r}")
                    
    # 0. Process past assignments first so we can adjust capacity
    past_f = set()
    past_s = set()
    em_idx = dates.index(emergency_date) if emergency_date and emergency_date in dates else 999
    
    if locked_assignments:
        for row in locked_assignments:
            d = row['exam_date']
            if d in dates:
                d_idx = dates.index(d)
                if d_idx < em_idx:
                    s = row['shift_name']
                    r = row['room_name']
                    p = row['person_name']
                    if row['role'].startswith('Faculty'):
                        past_f.add((p, d, s, r))
                    else:
                        past_s.add((p, d, s, r))

    # 1. Capacity per room
    for d in dates:
        d_idx = dates.index(d)
        is_past = (locked_assignments is not None) and (d_idx < em_idx)
        for s in shifts:
            for r in rooms:
                if is_past:
                    past_f_count = sum(1 for (f_p, d_p, s_p, r_p) in past_f if d_p == d and s_p == s and r_p == r)
                    past_s_count = sum(1 for (s_p, d_p, s_p2, r_p) in past_s if d_p == d and s_p2 == s and r_p == r)
                    model.Add(sum(x_fac[(f_id, d, s, r)] for f_id in faculties) == past_f_count)
                    model.Add(sum(x_stf[(s_id, d, s, r)] for s_id in staffData) == past_s_count)
                else:
                    model.Add(sum(x_fac[(f_id, d, s, r)] for f_id in faculties) == req_fac)
                    model.Add(sum(x_stf[(s_id, d, s, r)] for s_id in staffData) == req_stf)

    # 2. At most 1 room per person per shift
    for f_id in faculties:
        for d in dates:
            for s in shifts:
                model.Add(sum(x_fac[(f_id, d, s, r)] for r in rooms) <= 1)
                
    for s_id in staffData:
        for d in dates:
            for s in shifts:
                model.Add(sum(x_stf[(s_id, d, s, r)] for r in rooms) <= 1)
                
    # 3. Emergency Exclusions (Hard constraint)
    for f_id, info in faculties.items():
        excl = info.get("emergency_shifts", [])
        for d in dates:
            for s in shifts:
                shift_id = f"{d}-{s}"
                if shift_id in excl or d in excl:
                    for r in rooms:
                        model.Add(x_fac[(f_id, d, s, r)] == 0)
                        
    for s_id, info in staffData.items():
        excl = info.get("emergency_shifts", [])
        for d in dates:
            for s in shifts:
                shift_id = f"{d}-{s}"
                if shift_id in excl or d in excl:
                    for r in rooms:
                        model.Add(x_stf[(s_id, d, s, r)] == 0)

    # 3.5 Dynamic Rescheduling constraints
    if locked_assignments:
        for d in dates:
            if dates.index(d) < em_idx:
                for s in shifts:
                    for r in rooms:
                        for f_id in faculties:
                            if (f_id, d, s, r) in past_f:
                                model.Add(x_fac[(f_id, d, s, r)] == 1)
                            else:
                                model.Add(x_fac[(f_id, d, s, r)] == 0)
                        for s_id in staffData:
                            if (s_id, d, s, r) in past_s:
                                model.Add(x_stf[(s_id, d, s, r)] == 1)
                            else:
                                model.Add(x_stf[(s_id, d, s, r)] == 0)

    if emergency_absence and emergency_date:
        em_idx = dates.index(emergency_date) if emergency_date in dates else 999
        for d in dates:
            if dates.index(d) >= em_idx:
                for s in shifts:
                    for r in rooms:
                        if emergency_absence in faculties:
                            model.Add(x_fac[(emergency_absence, d, s, r)] == 0)
                        if emergency_absence in staffData:
                            model.Add(x_stf[(emergency_absence, d, s, r)] == 0)


    # Calculate individual workloads
    workload_fac = {}
    for f_id in faculties:
        workload_fac[f_id] = sum(x_fac[(f_id, d, s, r)] for d in dates for s in shifts for r in rooms)
        
    workload_stf = {}
    for s_id in staffData:
        workload_stf[s_id] = sum(x_stf[(s_id, d, s, r)] for d in dates for s in shifts for r in rooms)
        
    total_shifts_count = len(dates) * len(shifts) * len(rooms)
    max_fac_workload = model.NewIntVar(0, total_shifts_count, "max_fac_workload")
    min_fac_workload = model.NewIntVar(0, total_shifts_count, "min_fac_workload")
    max_stf_workload = model.NewIntVar(0, total_shifts_count, "max_stf_workload")
    min_stf_workload = model.NewIntVar(0, total_shifts_count, "min_stf_workload")
    
    if faculties:
        for f_id in faculties:
            if f_id != emergency_absence:
                model.Add(workload_fac[f_id] <= max_fac_workload)
                model.Add(workload_fac[f_id] >= min_fac_workload)
    else:
        model.Add(max_fac_workload == 0)
        model.Add(min_fac_workload == 0)
        
    if staffData:
        for s_id in staffData:
            if s_id != emergency_absence:
                model.Add(workload_stf[s_id] <= max_stf_workload)
                model.Add(workload_stf[s_id] >= min_stf_workload)
    else:
        model.Add(max_stf_workload == 0)
        model.Add(min_stf_workload == 0)

    # 4. Gaps (Penalty for working multiple shifts a day)
    # NEW: Initialize two_shift_preferences if not provided
    if two_shift_preferences is None:
        two_shift_preferences = []
    
    # Build a dict for quick lookup of who allows 2 shifts (FACULTY ONLY)
    # Default: False (restrict 2 shifts by default unless explicitly allowed)
    allow_two_shifts = {}
    for pref in two_shift_preferences:
        person = pref.get('person')
        allow = pref.get('allowTwoShifts', False)  # Default to RESTRICTING 2 shifts
        # Only apply to faculty, not staff
        if person in faculties:
            allow_two_shifts[person] = allow
    
    consecutive_penalties = []
    for f_id in faculties:
        for d in dates:
            shifts_today = sum(x_fac[(f_id, d, s, r)] for s in shifts for r in rooms)
            double_shift = model.NewBoolVar(f"F_ds_{f_id}_{d}")
            model.Add(shifts_today - 1 <= double_shift)
            # Only add penalty if person explicitly doesn't allow 2 shifts
            # Default (not set): False = restrict 2 shifts, apply penalty
            if not allow_two_shifts.get(f_id, False):
                consecutive_penalties.append(double_shift)
            
    for s_id in staffData:
        for d in dates:
            shifts_today = sum(x_stf[(s_id, d, s, r)] for s in shifts for r in rooms)
            double_shift = model.NewBoolVar(f"S_ds_{s_id}_{d}")
            model.Add(shifts_today - 1 <= double_shift)
            # Staff always gets the penalty (no two-shift preferences for staff)
            consecutive_penalties.append(double_shift)
            
    # 5. Priority bonuses
    priority_bonuses = []
    for f_id, info in faculties.items():
        for d in info.get("priority_dates", []):
            if d in dates:
                assigned_on_d = sum(x_fac[(f_id, d, s, r)] for s in shifts for r in rooms)
                priority_bonuses.append(assigned_on_d)
        for shift_id in info.get("priority_shifts", []):
            parts = shift_id.split("-")
            if len(parts) == 2:
                d, s = parts[0], parts[1]
                if d in dates and s in shifts:
                    assigned_on_shift = sum(x_fac[(f_id, d, s, r)] for r in rooms)
                    priority_bonuses.append(assigned_on_shift)
                
    for s_id, info in staffData.items():
        for d in info.get("priority_dates", []):
            if d in dates:
                assigned_on_d = sum(x_stf[(s_id, d, s, r)] for s in shifts for r in rooms)
                priority_bonuses.append(assigned_on_d)
        for shift_id in info.get("priority_shifts", []):
            parts = shift_id.split("-")
            if len(parts) == 2:
                d, s = parts[0], parts[1]
                if d in dates and s in shifts:
                    assigned_on_shift = sum(x_stf[(s_id, d, s, r)] for r in rooms)
                    priority_bonuses.append(assigned_on_shift)

    # Minimization Objective
    obj_terms = []
    obj_terms.append(max_fac_workload * 50)
    obj_terms.append((max_fac_workload - min_fac_workload) * 200)
    obj_terms.append(max_stf_workload * 50)
    obj_terms.append((max_stf_workload - min_stf_workload) * 200)
    
    for p in consecutive_penalties:
        obj_terms.append(p * 100)
    for b in priority_bonuses:
        obj_terms.append(b * -20)
        
    model.Minimize(sum(obj_terms))
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results = []
        for d in dates:
            for s in shifts:
                for r in rooms:
                    assigned_f = []
                    for f_id in faculties:
                        if solver.Value(x_fac[(f_id, d, s, r)]) == 1:
                            assigned_f.append(f_id)
                    assigned_s = []
                    for s_id in staffData:
                        if solver.Value(x_stf[(s_id, d, s, r)]) == 1:
                            assigned_s.append(s_id)
                            
                    results.append({
                        "Date": d, "Shift": s, "Room": r,
                        "faculties": assigned_f,
                        "staffs": assigned_s
                    })
        total_req = len(dates) * len(shifts) * len(rooms) * (req_fac + req_stf)
        return {"results": results, "flow": total_req, "total": total_req}
    else:
        return None

def formal_scheduler_api(teachers, staff, rooms, dates, preferences=None, two_shift_preferences=None, locked_assignments=None, emergency_absence=None, emergency_date=None, req_fac=2, req_stf=1):
    try:
        logger.info("🔶 Starting formal_scheduler_api")
        logger.info(f"📅 Exam dates received: {len(dates)} dates - {dates}")
        
        # Use provided data or read from database if not provided
        if not teachers:
            teachers = read_teachers()
        if not staff:
            staff = read_staff()
        if not rooms:
            rooms = read_rooms()
            
        if not teachers or not staff or not rooms or not dates:
            logger.error("❌ Missing critical data for scheduling")
            return [], {'message': 'Missing data: teachers, staff, rooms, or dates', 'empty_positions': 0, 'total_positions': 0}

        shifts = ["Morning", "Afternoon"]
        total_shifts = len(dates) * len(shifts)
        
        # Build facultyData and staffData dictionaries using names as keys for simplicity
        facultyData = {f_id: {"name": f_id, "priority_dates": [], "emergency_shifts": []} for f_id in teachers}
        staffData = {s_id: {"name": s_id, "priority_dates": [], "emergency_shifts": []} for s_id in staff}

        if preferences and isinstance(preferences, list):
            logger.info(f"📋 Processing {len(preferences)} preference rules")
            for idx, rule in enumerate(preferences):
                person = rule.get('teacher') or rule.get('staff') or rule.get('person')
                date_input = rule.get('date')
                status = rule.get('status')
                pref_shift = rule.get('shift', 'All')
                
                if not person or not date_input or not status:
                    continue

                if person not in teachers and person not in staff:
                    logger.warning(f"⚠️ Preference rule {idx}: person '{person}' not found in lists")
                    continue

                date_list = [d.strip() for d in str(date_input).split(',') if d.strip()]

                for d in date_list:
                    if d not in dates:
                        logger.warning(f"⚠️ Preference rule {idx}: date '{d}' not found in valid dates list")
                        continue

                    shifts_to_apply = ["Morning", "Afternoon"] if pref_shift == "All" else [pref_shift]

                    for s in shifts_to_apply:
                        shift_id = f"{d}-{s}"
                        if person in facultyData:
                            if status == 'emergency':
                                facultyData[person]["emergency_shifts"].append(shift_id)
                            elif status == 'preferred':
                                facultyData[person].setdefault("priority_shifts", []).append(shift_id)
                                
                        if person in staffData:
                            if status == 'emergency':
                                staffData[person]["emergency_shifts"].append(shift_id)
                            elif status == 'preferred':
                                staffData[person].setdefault("priority_shifts", []).append(shift_id)
                    
                    logger.info(f"  ✓ {person} on {d} ({pref_shift}): {status}")

        total_req = len(dates) * len(shifts) * len(rooms) * (req_fac + req_stf)
        
        # --- SOLVING ---
        logger.info("\n[STATUS] Computational Engine Active. Optimizing deployment...")
        cp_solution = solve_with_ortools(dates, rooms, shifts, facultyData, staffData, req_fac=req_fac, req_stf=req_stf, two_shift_preferences=two_shift_preferences, locked_assignments=locked_assignments, emergency_absence=emergency_absence, emergency_date=emergency_date)
        
        if cp_solution:
            logger.info("[OR-TOOLS] Solved with advanced constraint programming for gaps and workload management!")
            raw_results = cp_solution["results"]
            current_flow = cp_solution["flow"]
        else:
            logger.info("[FALLBACK] Using standard NetworkX Engine (possibly due to infeasibility)...")
            G = nx.DiGraph()
            source, sink = "SOURCE", "SINK"
            
            for f_id in teachers:
                for w_idx in range(1, total_shifts + 1):
                    w_node = f"{f_id}_W_{w_idx}"
                    G.add_edge(source, w_node, capacity=1, weight=(w_idx - 1) * 150)
                    G.add_edge(w_node, f_id, capacity=1, weight=0)
            
            for s_id in staff:
                for w_idx in range(1, total_shifts + 1):
                    w_node = f"{s_id}_W_{w_idx}"
                    G.add_edge(source, w_node, capacity=1, weight=(w_idx - 1) * 150)
                    G.add_edge(w_node, s_id, capacity=1, weight=0)
            
            def add_personnel_edges(person_id, person_info, req_prefix):
                for d in dates:
                    date_node = f"{person_id}_{d}"
                    G.add_edge(person_id, date_node, capacity=2, weight=0)
                    for s in shifts:
                        shift_id = f"{d}-{s}"
                        shift_node = f"{person_id}_{shift_id}"
                        
                        if shift_id in person_info.get("emergency_shifts", []) or d in person_info.get("emergency_shifts", []):
                            cost = 5000
                        elif shift_id in person_info.get("priority_shifts", []) or d in person_info.get("priority_dates", []):
                            # Simple weighting if it matches a priority date
                            cost = 10
                        else:
                            cost = 200
                        
                        G.add_edge(date_node, shift_node, capacity=1, weight=cost)
                        
                        for r in rooms:
                            req_node = f"{req_prefix}_REQ_{d}_{s}_{r}"
                            G.add_edge(shift_node, req_node, capacity=1, weight=0)
                            
            for f_id, info in facultyData.items():
                add_personnel_edges(f_id, info, "F")
            for s_id, info in staffData.items():
                add_personnel_edges(s_id, info, "S")
                
            for d in dates:
                for s in shifts:
                    for r in rooms:
                        G.add_edge(f"F_REQ_{d}_{s}_{r}", sink, capacity=req_fac, weight=0)
                        G.add_edge(f"S_REQ_{d}_{s}_{r}", sink, capacity=req_stf, weight=0)
                        
            try:
                flow_dict = nx.max_flow_min_cost(G, source, sink)
                current_flow = nx.maximum_flow(G, source, sink)[0]
            except Exception as e:
                logger.error(f"[ERROR] Logic Error: {e}")
                return [], {'message': f'Logic Error: {e}', 'empty_positions': total_req, 'total_positions': total_req}
            
            raw_results = []
            for d in dates:
                for s in shifts:
                    for r in rooms:
                        f_req = f"F_REQ_{d}_{s}_{r}"
                        s_req = f"S_REQ_{d}_{s}_{r}"
                        
                        assigned_f = []
                        for f_id in teachers:
                            shift_node = f"{f_id}_{d}-{s}"
                            if flow_dict.get(shift_node, {}).get(f_req, 0) > 0:
                                assigned_f.append(f_id)
                        
                        assigned_s = []
                        for s_id in staff:
                            shift_node = f"{s_id}_{d}-{s}"
                            if flow_dict.get(shift_node, {}).get(s_req, 0) > 0:
                                assigned_s.append(s_id)
                        
                        raw_results.append({
                            "Date": d, "Shift": s, "Room": r,
                            "faculties": assigned_f,
                            "staffs": assigned_s
                        })
                        
        empty_positions = 0
        final_results = []
        
        for item in raw_results:
            d = item["Date"]
            s = item["Shift"]
            r = item["Room"]
            
            assigned_f = item.get("faculties", [])
            assigned_s = item.get("staffs", [])
            
            empty_positions += max(0, req_fac - len(assigned_f))
            empty_positions += max(0, req_stf - len(assigned_s))
            
            f_indices = [teachers.index(f) if f in teachers else -1 for f in assigned_f]
            s_indices = [staff.index(st) if st in staff else -1 for st in assigned_s]
            
            final_results.append({
                'date': dates.index(d),
                'shift': shifts.index(s),
                'room': rooms.index(r),
                'faculties': f_indices,
                'staffs': s_indices
            })
        
        status_msg = f'Schedule generated with {empty_positions} empty positions out of {total_req} total slots'
        if empty_positions == 0:
            status_msg = f'✔ Deployment Successful. All positions filled.'
            
        status = {
            'message': status_msg,
            'empty_positions': empty_positions,
            'total_positions': total_req
        }
        
        logger.info("🎉 formal_scheduler_api completed successfully")
        return final_results, status

    except Exception as e:
        logger.error(f"❌ Exception in formal_scheduler_api: {str(e)}")
        return [], {'message': f'Error: {str(e)}', 'empty_positions': 0, 'total_positions': 0}

def display_schedule(results, teachers, staff, rooms, dates, version_name=None):
    shifts = ["Morning", "Afternoon"]
    
    logger.info("━" * 80)
    logger.info("🖨️  DISPLAY_SCHEDULE STARTED")
    
    print("\n" + "="*100)
    print("FINAL EXAM SCHEDULE".center(110))
    print("="*110)

    csv_data = []
    
    # Determine req_fac and req_stf from the max length in all results
    req_fac = 2
    req_stf = 1
    if results:
        req_fac = max([len(r.get('faculties', [])) for r in results] + [2])
        req_stf = max([len(r.get('staffs', [])) for r in results] + [1])
    
    fac_cols = [f'Faculty{i+1}' for i in range(req_fac)]
    stf_cols = [f'Staff{i+1}' for i in range(req_stf)]
    header_cols = ['Date', 'Room', 'Shift'] + fac_cols + stf_cols
    
    col_header = ' | '.join(f"{h:<20}" for h in header_cols)
    print(col_header)
    print("-" * 110)

    for date_idx, date in enumerate(dates):
        for room_idx, room in enumerate(rooms):
            for shift_idx, shift_name in enumerate(shifts):
                fac_names = [''] * req_fac
                stf_names = [''] * req_stf
                
                for r in results:
                    if r['date'] == date_idx and r['room'] == room_idx and r['shift'] == shift_idx:
                        fac_idxs = r.get('faculties', [])
                        stf_idxs = r.get('staffs', [])
                        for i, fi in enumerate(fac_idxs):
                            if i < req_fac and 0 <= fi < len(teachers):
                                fac_names[i] = teachers[fi]
                        for i, si in enumerate(stf_idxs):
                            if i < req_stf and 0 <= si < len(staff):
                                stf_names[i] = staff[si]
                        break
                
                row = {'Date': date, 'Room': room, 'Shift': shift_name}
                for i, col in enumerate(fac_cols):
                    row[col] = fac_names[i]
                for i, col in enumerate(stf_cols):
                    row[col] = stf_names[i]
                
                csv_data.append(row)
                row_str = ' | '.join(f"{str(row.get(h,'')):<20}" for h in header_cols)
                print(row_str)

    print("="*110)
    if csv_data:
        df = pd.DataFrame(csv_data)
        
        schedule_storage = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schedule_storage')
        if not os.path.exists(schedule_storage):
            os.makedirs(schedule_storage)
        
        # Save main schedule with constant filename (will overwrite)
        main_csv_path = os.path.join(schedule_storage, MAIN_SCHEDULE_CSV)
        df.to_csv(main_csv_path, index=False)
        logger.info(f"✓ Main schedule saved: {main_csv_path}")
        
        # Generate Teacher Schedule: one row per person per assignment
        teacher_rows_list = []
        for col in fac_cols:
            if col in df.columns:
                for _, row in df.iterrows():
                    person = row[col]
                    if person and person != '':
                        teacher_rows_list.append({
                            'Date': row['Date'], 'Shift': row['Shift'], 'Room': row['Room'],
                            'Teacher': person, 'Role': col
                        })
        if teacher_rows_list:
            teacher_df = pd.DataFrame(teacher_rows_list)
            teacher_schedule_path = os.path.join(schedule_storage, TEACHER_SCHEDULE_CSV)
            teacher_df.to_csv(teacher_schedule_path, index=False)
            logger.info(f"✓ Teacher schedule saved: {teacher_schedule_path}")
        
        # Generate Staff Schedule: one row per staff per assignment
        staff_rows_list = []
        for col in stf_cols:
            if col in df.columns:
                for _, row in df.iterrows():
                    person = row[col]
                    if person and person != '':
                        staff_rows_list.append({
                            'Date': row['Date'], 'Shift': row['Shift'], 'Room': row['Room'],
                            'Staff': person, 'Role': col
                        })
        if staff_rows_list:
            staff_df = pd.DataFrame(staff_rows_list)
            staff_schedule_path = os.path.join(schedule_storage, STAFF_SCHEDULE_CSV)
            staff_df.to_csv(staff_schedule_path, index=False)
            logger.info(f"✓ Staff schedule saved: {staff_schedule_path}")
        
        # Generate Room Schedule (full table grouped by Room)
        if 'Room' in df.columns:
            room_schedule_path = os.path.join(schedule_storage, ROOM_SCHEDULE_CSV)
            df.to_csv(room_schedule_path, index=False)
            logger.info(f"✓ Room schedule saved: {room_schedule_path}")
        
        return main_csv_path
    
    return None

def main():
    teachers = read_teachers()
    staff = read_staff()
    rooms = read_rooms()
    dates = ["2024-01-15", "2024-01-16", "2024-01-17"]
    
    if not teachers or not staff or not rooms:
        print("Missing database data.")
        return
    
    results, status = formal_scheduler_api(teachers, staff, rooms, dates)
    print(f"\nScheduling completed: {status['message']}")
    
    csv_path = display_schedule(results, teachers, staff, rooms, dates)
    if csv_path:
        print(f"\n✅ Schedule CSV generated successfully: {os.path.basename(csv_path)}")

if __name__ == "__main__":
    main()