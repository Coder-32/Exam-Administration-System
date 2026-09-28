import os
import sys
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from config import Config
except ImportError:
    from CONFIG import Config

from flask import Flask
from flask_login import LoginManager
from routes import register_routes
from service.db import get_user_by_id

# Configure root logger with Windows console-safe encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Application factory for Exam Administration System."""
    app = Flask(
        __name__,
        template_folder=os.path.join(Config.BASE_DIR, 'templates'),
        static_folder=os.path.join(Config.BASE_DIR, 'static')
    )
    app.config.from_object(config_class)
    app.secret_key = config_class.SECRET_KEY

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(int(user_id))

    # Register all modular route blueprints
    register_routes(app)

    logger.info('[OK] Exam Scheduling System initialized successfully')
    logger.info(f'[INFO] Schedule storage directory: {Config.SCHEDULE_STORAGE_DIR}')
    return app

app = create_app()

if __name__ == '__main__':
    port = Config.PORT
    debug = Config.DEBUG
    logger.info(f'Starting server on http://localhost:{port} (debug={debug})')
    app.run(debug=debug, port=port, host='0.0.0.0')
