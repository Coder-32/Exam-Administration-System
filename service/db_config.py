import os

# PostgreSQL Database Configuration
# Uses DATABASE_URL if present (for Render/production), otherwise uses individual env vars or defaults
DATABASE_URL = os.environ.get('DATABASE_URL')

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'postgres'),
    'database': os.environ.get('DB_NAME', 'exam_db'),
    'port': int(os.environ.get('DB_PORT', 5432))
}
