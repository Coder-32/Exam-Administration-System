from routes.auth_routes import auth_bp
from routes.view_routes import views_bp
from routes.personnel_routes import personnel_bp
from routes.schedule_routes import schedule_bp
from routes.export_routes import export_bp

def register_routes(app):
    """Register all application route blueprints."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(personnel_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(export_bp)
