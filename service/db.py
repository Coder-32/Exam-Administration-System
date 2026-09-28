import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from config import Config
except ImportError:
    from CONFIG import Config

logger = logging.getLogger(__name__)

# ==========================================
# USER CLASS FOR FLASK-LOGIN
# ==========================================

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username
        self.password = None

# ==========================================
# SQLITE DATABASE CONNECTION & INITIALIZATION
# ==========================================

DB_PATH = Config.SQLITE_DB_PATH

def get_db_connection():
    """Returns an active SQLite connection with row_factory for dict-like access."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def setup_database():
    """Initialize SQLite database tables and indexes."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # 1. Users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )""")

        # Helper to check and add user_id column if migrating an older schema
        def add_user_id_if_missing(table_name):
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cur.fetchall()]
            if 'user_id' not in columns:
                logger.info(f"Adding user_id column to {table_name}...")
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER DEFAULT 1")

        # 2. Teachers table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        add_user_id_if_missing('teachers')

        # 3. Staffs table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS staffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        add_user_id_if_missing('staffs')

        # 4. Rooms table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        add_user_id_if_missing('rooms')

        # 5. Schedules metadata table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            version_name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        add_user_id_if_missing('schedules')

        # 6. Assignments table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            exam_date TEXT NOT NULL,
            shift_name TEXT NOT NULL,
            room_name TEXT NOT NULL,
            role TEXT NOT NULL,
            person_name TEXT NOT NULL,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
        )""")

        conn.commit()
        logger.info(f"✓ SQLite database initialized successfully at: {DB_PATH}")
    except Exception as e:
        logger.error(f"Error setting up SQLite database: {e}")
        raise
    finally:
        conn.close()

# Initialize tables upon module import
setup_database()

# ==========================================
# AUTHENTICATION HELPERS
# ==========================================

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return User(row['id'], row['username']) if row else None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            u = User(row['id'], row['username'])
            u.password = row['password']
            return u
        return None
    finally:
        conn.close()

def create_user(username, password):
    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_password(user_id, new_password):
    """Update a user's password with a new hashed version."""
    hashed_pw = generate_password_hash(new_password)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating SQLite password: {e}")
        return False
    finally:
        conn.close()

def delete_user(user_id):
    """Delete a user account and all associated data via foreign key cascades."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting SQLite user: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# MASTER DATA OPERATIONS (Teachers, Staff, Rooms)
# ==========================================

def read_teachers(user_id=None):
    """Read all teachers for a specific user, or all if user_id is None."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute("SELECT name FROM teachers WHERE user_id = ? ORDER BY name", (user_id,))
        else:
            cur.execute("SELECT name FROM teachers ORDER BY name")
        names = [row['name'] for row in cur.fetchall()]
        if not names:
            txt_path = os.path.join(Config.DATABASE_DIR, 'teachers.txt')
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    names = [line.strip() for line in f if line.strip()]
        return names
    finally:
        conn.close()

def read_staff(user_id=None):
    """Read all staff for a specific user, or all if user_id is None."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute("SELECT name FROM staffs WHERE user_id = ? ORDER BY name", (user_id,))
        else:
            cur.execute("SELECT name FROM staffs ORDER BY name")
        names = [row['name'] for row in cur.fetchall()]
        if not names:
            txt_path = os.path.join(Config.DATABASE_DIR, 'staffs.txt')
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    names = [line.strip() for line in f if line.strip()]
        return names
    finally:
        conn.close()

def read_rooms(user_id=None):
    """Read all rooms for a specific user, or all if user_id is None."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute("SELECT name FROM rooms WHERE user_id = ? ORDER BY name", (user_id,))
        else:
            cur.execute("SELECT name FROM rooms ORDER BY name")
        names = [row['name'] for row in cur.fetchall()]
        if not names:
            txt_path = os.path.join(Config.DATABASE_DIR, 'rooms.txt')
            if os.path.exists(txt_path):
                with open(txt_path, 'r', encoding='utf-8') as f:
                    names = [line.strip() for line in f if line.strip()]
        return names
    finally:
        conn.close()

def add_teacher(user_id, name):
    """Add a teacher to the database for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM teachers WHERE user_id = ? AND name = ?", (user_id, name))
        if cur.fetchone():
            return False
        cur.execute("INSERT INTO teachers (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        return True
    finally:
        conn.close()

def add_staff(user_id, name):
    """Add a staff member to the database for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM staffs WHERE user_id = ? AND name = ?", (user_id, name))
        if cur.fetchone():
            return False
        cur.execute("INSERT INTO staffs (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        return True
    finally:
        conn.close()

def add_room(user_id, name):
    """Add a room to the database for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM rooms WHERE user_id = ? AND name = ?", (user_id, name))
        if cur.fetchone():
            return False
        cur.execute("INSERT INTO rooms (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        return True
    finally:
        conn.close()

def delete_teacher(user_id, name):
    """Delete a teacher for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM teachers WHERE user_id = ? AND name = ?", (user_id, name))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_staff(user_id, name):
    """Delete a staff member for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM staffs WHERE user_id = ? AND name = ?", (user_id, name))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_room(user_id, name):
    """Delete a room for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM rooms WHERE user_id = ? AND name = ?", (user_id, name))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def get_all_data(user_id):
    """Get all personnel and room data for a specific user."""
    return {
        'teachers': read_teachers(user_id),
        'staff': read_staff(user_id),
        'rooms': read_rooms(user_id)
    }

def delete_all_teachers(user_id):
    """Delete all teachers for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM teachers WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def delete_all_staff(user_id):
    """Delete all staff for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM staffs WHERE user_id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

# ==========================================
# SCHEDULE & ROUTINE DB OPERATIONS
# ==========================================

def _insert_assignments(cursor, schedule_id, schedule_results):
    """Helper to insert assignment records into SQLite."""
    sql = ("INSERT INTO assignments (schedule_id, exam_date, shift_name, room_name, role, person_name) "
           "VALUES (?, ?, ?, ?, ?, ?)")
    for row in schedule_results:
        exam_date = row.get("Date")
        shift_name = row.get("Shift")
        room_name = row.get("Room")

        faculties = list(row.get("faculties", []))
        staffs = list(row.get("staffs", []))

        # Backward compatibility for flat fields
        if not faculties:
            f1 = row.get("Faculty1", row.get("Faculty_1", ""))
            f2 = row.get("Faculty2", row.get("Faculty_2", ""))
            if f1 and f1 != "---": faculties.append(f1)
            if f2 and f2 != "---": faculties.append(f2)
        if not staffs:
            s1 = row.get("Staff", row.get("Staff1", ""))
            if s1 and s1 != "---": staffs.append(s1)

        for i, name in enumerate(faculties):
            if name and name not in ("---", "N/A", ""):
                cursor.execute(sql, (schedule_id, exam_date, shift_name, room_name, f'Faculty_{i+1}', name))
        for i, name in enumerate(staffs):
            if name and name not in ("---", "N/A", ""):
                cursor.execute(sql, (schedule_id, exam_date, shift_name, room_name, f'Staff_{i+1}', name))

def save_schedule_to_db(user_id, version_name, schedule_results):
    """Saves the generated routine and assignments for a user in SQLite."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
            "INSERT INTO schedules (user_id, version_name, created_at) VALUES (?, ?, ?)",
            (user_id, version_name, ist_now)
        )
        schedule_id = cur.lastrowid
        _insert_assignments(cur, schedule_id, schedule_results)
        conn.commit()
        return schedule_id
    finally:
        conn.close()

def _rows_to_dicts(rows):
    return [dict(row) for row in rows]

def get_latest_schedule_assignments(user_id):
    """Gets the latest assignments for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM schedules WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
        row = cur.fetchone()
        if not row:
            return []
        cur.execute("SELECT * FROM assignments WHERE schedule_id = ?", (row['id'],))
        return _rows_to_dicts(cur.fetchall())
    finally:
        conn.close()

def get_all_schedules(user_id):
    """Gets all schedules for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, version_name, created_at FROM schedules WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return _rows_to_dicts(cur.fetchall())
    finally:
        conn.close()

def get_schedule_assignments(user_id, schedule_id):
    """Gets assignments of a specific schedule ID (only if owned by user)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id))
        if not cur.fetchone():
            return []
        cur.execute("SELECT * FROM assignments WHERE schedule_id = ?", (schedule_id,))
        return _rows_to_dicts(cur.fetchall())
    finally:
        conn.close()

def delete_schedule(user_id, schedule_id):
    """Deletes a schedule for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def rename_schedule(user_id, schedule_id, new_name):
    """Renames a schedule for a user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE schedules SET version_name = ? WHERE id = ? AND user_id = ?",
            (new_name, schedule_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()