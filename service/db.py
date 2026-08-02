import os
import logging
import sys
import time
import sqlite3
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

from service.db_config import DB_CONFIG, DATABASE_URL

# ==========================================
# USER CLASS FOR FLASK-LOGIN
# ==========================================

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# ==========================================
# DATABASE BACKEND DETECTION
# PostgreSQL is used on Render (when DATABASE_URL is set or PG is reachable).
# SQLite is used as a local fallback when PostgreSQL is not available.
# ==========================================

_use_sqlite = False
_sqlite_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'local_schedules.db')
_last_db_error = None

def _try_postgres():
    """Attempt to connect to PostgreSQL. Returns conn or None."""
    global _last_db_error
    try:
        import psycopg2
        import psycopg2.extras
        if DATABASE_URL:
            conn = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.DictCursor,
                connect_timeout=2
            )
        else:
            conn = psycopg2.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                dbname=DB_CONFIG['database'],
                port=DB_CONFIG['port'],
                cursor_factory=psycopg2.extras.DictCursor,
                connect_timeout=2
            )
        _last_db_error = None
        return conn
    except Exception as e:
        _last_db_error = str(e)
        logger.warning(f"PostgreSQL unavailable: {e}")
        return None

def get_last_db_error():
    return _last_db_error

def get_db_connection():
    """Returns a PostgreSQL connection, or None if unavailable."""
    return _try_postgres()

# ==========================================
# SQLITE FALLBACK HELPERS
# ==========================================

def _get_sqlite_conn():
    """Returns a SQLite connection with row_factory for dict-like access."""
    os.makedirs(os.path.dirname(_sqlite_path), exist_ok=True)
    conn = sqlite3.connect(_sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn

def _setup_sqlite():
    conn = _get_sqlite_conn()
    try:
        cur = conn.cursor()
        
        # Create users table first
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )""")
        
        # Helper to add user_id if missing
        def add_user_id_if_missing(table_name):
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cur.fetchall()]
            if 'user_id' not in columns:
                logger.info(f"Adding user_id column to {table_name}...")
                # Add with a default of 1 if there's already data (assuming first user)
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER DEFAULT 1")

        # Create or migrate other tables
        cur.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )""")
        add_user_id_if_missing('teachers')

        cur.execute("""
        CREATE TABLE IF NOT EXISTS staffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )""")
        add_user_id_if_missing('staffs')

        cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )""")
        add_user_id_if_missing('rooms')

        cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )""")
        add_user_id_if_missing('schedules')

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
        logger.info("✓ SQLite fallback tables created/verified/migrated")
    finally:
        conn.close()

# ==========================================
# TABLE SETUP
# ==========================================

def setup_database():
    """Create PostgreSQL tables if using PostgreSQL."""
    import psycopg2
    conn = get_db_connection()
    if not conn:
        raise ConnectionError(f"Cannot connect to PostgreSQL: {get_last_db_error()}")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password TEXT NOT NULL
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS staffs (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                version_name VARCHAR(100) NOT NULL,
                created_at VARCHAR(50),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                schedule_id INT NOT NULL,
                exam_date VARCHAR(50) NOT NULL,
                shift_name VARCHAR(50) NOT NULL,
                room_name VARCHAR(50) NOT NULL,
                role VARCHAR(50) NOT NULL,
                person_name VARCHAR(255) NOT NULL,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
            )""")
        conn.commit()
        logger.info("✓ PostgreSQL tables created/verified")
    except Exception as e:
        logger.error(f"Error setting up PostgreSQL tables: {e}")
        raise
    finally:
        conn.close()


def _init_db_with_retry():
    """Try PostgreSQL first. Fall back to SQLite if unavailable.
    On Render (DATABASE_URL set): retry 5 times with delay to handle cold starts.
    Locally (no DATABASE_URL): try once only, then immediately fall back to SQLite."""
    global _use_sqlite
    from service.db_config import DATABASE_URL as _db_url
    max_retries = 5 if _db_url else 1
    delay = 2 if _db_url else 0

    for attempt in range(1, max_retries + 1):
        try:
            setup_database()
            _use_sqlite = False
            logger.info("✓ Using PostgreSQL for schedule storage")
            return
        except Exception as e:
            logger.warning(f"PG init attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(delay)

    # PostgreSQL not available — use SQLite locally
    logger.warning("⚠️  PostgreSQL not available. Falling back to SQLite for local development.")
    _setup_sqlite()
    _use_sqlite = True

_init_db_with_retry()

# ==========================================
# AUTHENTICATION HELPERS
# ==========================================

def get_user_by_id(user_id):
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
            return User(row['id'], row['username']) if row else None
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return None
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                return User(row['id'], row['username']) if row else None
        finally:
            conn.close()

def get_user_by_username(username):
    if _use_sqlite:
        conn = _get_sqlite_conn()
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
    else:
        conn = get_db_connection()
        if not conn: return None
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
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
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

def update_password(user_id, new_password):
    """Update a user's password with a new hashed version"""
    hashed_pw = generate_password_hash(new_password)
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating SQLite password: {e}")
            return False
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_pw, user_id))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating PostgreSQL password: {e}")
            return False
        finally:
            conn.close()

def delete_user(user_id):
    """Delete a user account and all associated data (cascading)"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON") # Ensure cascade works in SQLite
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting SQLite user: {e}")
            return False
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting PostgreSQL user: {e}")
            return False
        finally:
            conn.close()

# ==========================================
# MASTER DATA OPERATIONS (Now in DB)
# ==========================================

def read_teachers(user_id):
    """Read all teachers for a specific user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM teachers WHERE user_id = ? ORDER BY name", (user_id,))
            return [row['name'] for row in cur.fetchall()]
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM teachers WHERE user_id = %s ORDER BY name", (user_id,))
                return [row['name'] for row in cur.fetchall()]
        finally:
            conn.close()

def read_staff(user_id):
    """Read all staff for a specific user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM staffs WHERE user_id = ? ORDER BY name", (user_id,))
            return [row['name'] for row in cur.fetchall()]
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM staffs WHERE user_id = %s ORDER BY name", (user_id,))
                return [row['name'] for row in cur.fetchall()]
        finally:
            conn.close()

def read_rooms(user_id):
    """Read all rooms for a specific user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM rooms WHERE user_id = ? ORDER BY name", (user_id,))
            return [row['name'] for row in cur.fetchall()]
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM rooms WHERE user_id = %s ORDER BY name", (user_id,))
                return [row['name'] for row in cur.fetchall()]
        finally:
            conn.close()

def add_teacher(user_id, name):
    """Add a teacher to the database for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM teachers WHERE user_id = ? AND name = ?", (user_id, name))
            if cur.fetchone(): return False
            cur.execute("INSERT INTO teachers (user_id, name) VALUES (?, ?)", (user_id, name))
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM teachers WHERE user_id = %s AND name = %s", (user_id, name))
                if cur.fetchone(): return False
                cur.execute("INSERT INTO teachers (user_id, name) VALUES (%s, %s)", (user_id, name))
            conn.commit()
            return True
        finally:
            conn.close()

def add_staff(user_id, name):
    """Add a staff member to the database for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM staffs WHERE user_id = ? AND name = ?", (user_id, name))
            if cur.fetchone(): return False
            cur.execute("INSERT INTO staffs (user_id, name) VALUES (?, ?)", (user_id, name))
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM staffs WHERE user_id = %s AND name = %s", (user_id, name))
                if cur.fetchone(): return False
                cur.execute("INSERT INTO staffs (user_id, name) VALUES (%s, %s)", (user_id, name))
            conn.commit()
            return True
        finally:
            conn.close()

def add_room(user_id, name):
    """Add a room to the database for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM rooms WHERE user_id = ? AND name = ?", (user_id, name))
            if cur.fetchone(): return False
            cur.execute("INSERT INTO rooms (user_id, name) VALUES (?, ?)", (user_id, name))
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM rooms WHERE user_id = %s AND name = %s", (user_id, name))
                if cur.fetchone(): return False
                cur.execute("INSERT INTO rooms (user_id, name) VALUES (%s, %s)", (user_id, name))
            conn.commit()
            return True
        finally:
            conn.close()

def delete_teacher(user_id, name):
    """Delete a teacher for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM teachers WHERE user_id = ? AND name = ?", (user_id, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM teachers WHERE user_id = %s AND name = %s", (user_id, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

def delete_staff(user_id, name):
    """Delete a staff member for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM staffs WHERE user_id = ? AND name = ?", (user_id, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM staffs WHERE user_id = %s AND name = %s", (user_id, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

def delete_room(user_id, name):
    """Delete a room for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM rooms WHERE user_id = ? AND name = ?", (user_id, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rooms WHERE user_id = %s AND name = %s", (user_id, name))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

def get_all_data(user_id):
    """Get all data for a specific user"""
    return {
        'teachers': read_teachers(user_id),
        'staff': read_staff(user_id),
        'rooms': read_rooms(user_id)
    }

def delete_all_teachers(user_id):
    """Delete all teachers for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM teachers WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM teachers WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

def delete_all_staff(user_id):
    """Delete all staff for a user"""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM staffs WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM staffs WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

# ==========================================
# SCHEDULE DB OPERATIONS (User-Scoped)
# ==========================================

def _insert_assignments(cursor, schedule_id, schedule_results, placeholder='%s'):
    """Shared logic to insert assignment rows."""
    for row in schedule_results:
        exam_date = row.get("Date")
        shift_name = row.get("Shift")
        room_name = row.get("Room")

        faculties = list(row.get("faculties", []))
        staffs = list(row.get("staffs", []))

        # Legacy fallback
        if not faculties:
            f1 = row.get("Faculty1", row.get("Faculty_1", ""))
            f2 = row.get("Faculty2", row.get("Faculty_2", ""))
            if f1 and f1 != "---": faculties.append(f1)
            if f2 and f2 != "---": faculties.append(f2)
        if not staffs:
            s1 = row.get("Staff", row.get("Staff1", ""))
            if s1 and s1 != "---": staffs.append(s1)

        sql = (f"INSERT INTO assignments (schedule_id, exam_date, shift_name, room_name, role, person_name) "
               f"VALUES ({placeholder},{placeholder},{placeholder},{placeholder},{placeholder},{placeholder})")

        for i, name in enumerate(faculties):
            if name and name not in ("---", "N/A", ""):
                cursor.execute(sql, (schedule_id, exam_date, shift_name, room_name, f'Faculty_{i+1}', name))
        for i, name in enumerate(staffs):
            if name and name not in ("---", "N/A", ""):
                cursor.execute(sql, (schedule_id, exam_date, shift_name, room_name, f'Staff_{i+1}', name))


def save_schedule_to_db(user_id, version_name, schedule_results):
    """Saves the schedule for a specific user."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            from datetime import timedelta
            ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO schedules (user_id, version_name, created_at) VALUES (?, ?, ?)", (user_id, version_name, ist_now))
            schedule_id = cur.lastrowid
            _insert_assignments(cur, schedule_id, schedule_results, placeholder='?')
            conn.commit()
            return schedule_id
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: raise ConnectionError("Database unavailable")
        try:
            with conn.cursor() as cur:
                from datetime import timedelta
                ist_now = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
                cur.execute("INSERT INTO schedules (user_id, version_name, created_at) VALUES (%s, %s, %s) RETURNING id", (user_id, version_name, ist_now))
                schedule_id = cur.fetchone()['id']
                _insert_assignments(cur, schedule_id, schedule_results, placeholder='%s')
            conn.commit()
            return schedule_id
        finally:
            conn.close()

def _rows_to_dicts(rows):
    return [dict(row) for row in rows]

def get_latest_schedule_assignments(user_id):
    """Gets the latest assignments for a user."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM schedules WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            row = cur.fetchone()
            if not row: return []
            cur.execute("SELECT * FROM assignments WHERE schedule_id = ?", (row['id'],))
            return _rows_to_dicts(cur.fetchall())
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM schedules WHERE user_id = %s ORDER BY id DESC LIMIT 1", (user_id,))
                latest = cur.fetchone()
                if not latest: return []
                cur.execute("SELECT * FROM assignments WHERE schedule_id = %s", (latest['id'],))
                return _rows_to_dicts(cur.fetchall())
        finally:
            conn.close()

def get_all_schedules(user_id):
    """Gets all schedules for a user."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, version_name, created_at FROM schedules WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            return _rows_to_dicts(cur.fetchall())
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, version_name, created_at FROM schedules WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                return _rows_to_dicts(cur.fetchall())
        finally:
            conn.close()

def get_schedule_assignments(user_id, schedule_id):
    """Gets assignments of a specific schedule ID (only if owned by user)."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            # Verify ownership
            cur.execute("SELECT 1 FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id))
            if not cur.fetchone(): return []
            cur.execute("SELECT * FROM assignments WHERE schedule_id = ?", (schedule_id,))
            return _rows_to_dicts(cur.fetchall())
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return []
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM schedules WHERE id = %s AND user_id = %s", (schedule_id, user_id))
                if not cur.fetchone(): return []
                cur.execute("SELECT * FROM assignments WHERE schedule_id = %s", (schedule_id,))
                return _rows_to_dicts(cur.fetchall())
        finally:
            conn.close()

def delete_schedule(user_id, schedule_id):
    """Deletes a schedule for a user."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM schedules WHERE id = ? AND user_id = ?", (schedule_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM schedules WHERE id = %s AND user_id = %s", (schedule_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

def rename_schedule(user_id, schedule_id, new_name):
    """Renames a schedule for a user."""
    if _use_sqlite:
        conn = _get_sqlite_conn()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE schedules SET version_name = ? WHERE id = ? AND user_id = ?", (new_name, schedule_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        if not conn: return False
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE schedules SET version_name = %s WHERE id = %s AND user_id = %s", (new_name, schedule_id, user_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
    conn.close()