import os
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Automatically load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass

SCHEDULE_STORAGE_DIR = os.path.join(BASE_DIR, 'schedule_storage')
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
SQLITE_DB_PATH = os.path.join(DATABASE_DIR, 'exam_schedules.db')

# Ensure necessary directories exist
os.makedirs(SCHEDULE_STORAGE_DIR, exist_ok=True)
os.makedirs(DATABASE_DIR, exist_ok=True)

class Config:
    """Application configuration parameters."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam-system-secret-key-2026')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    
    # Directory & database paths
    BASE_DIR = BASE_DIR
    SCHEDULE_STORAGE_DIR = SCHEDULE_STORAGE_DIR
    DATABASE_DIR = DATABASE_DIR
    SQLITE_DB_PATH = os.environ.get('SQLITE_DB_PATH', SQLITE_DB_PATH)
    
    # Filenames for generated schedules
    MAIN_SCHEDULE_CSV = "exam_schedule.csv"
    TEACHER_SCHEDULE_CSV = "teacher_schedule.csv"
    STAFF_SCHEDULE_CSV = "staff_schedule.csv"
    ROOM_SCHEDULE_CSV = "room_schedule.csv"
    
    # OCR / Tesseract configuration
    TESSERACT_CMD = os.environ.get(
        'TESSERACT_CMD',
        r'C:\Program Files\Tesseract-OCR\tesseract.exe' if platform.system() == 'Windows' else 'tesseract'
    )
