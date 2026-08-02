"""
Configuration and Setup Helper
This file provides information about configuring the application
"""

# ============================================================================
# SYSTEM REQUIREMENTS
# ============================================================================

SYSTEM_REQUIREMENTS = {
    'Python': '3.8 or higher',
    'pip': 'Latest version',
    'RAM': '2GB minimum',
    'Disk': '100MB free space',
    'Browser': 'Modern browser (Chrome, Firefox, Edge, Safari)'
}

# ============================================================================
# DEPENDENCIES
# ============================================================================

DEPENDENCIES = {
    'Flask': '2.3.2',           # Web framework
    'pandas': '2.0.3',          # Data manipulation
    'networkx': '3.1',          # Graph algorithms
    'openpyxl': '3.1.2'         # Excel file handling
}

# ============================================================================
# INSTALLATION STEPS
# ============================================================================

INSTALLATION_STEPS = """
1. Navigate to project directory:
   cd project_1_did

2. Install Python dependencies:
   pip install -r requirements.txt

3. Verify installation:
   python -c "import flask, pandas, networkx, openpyxl; print('All dependencies installed!')"

4. Run the application:
   python app.py

5. Open browser:
   http://localhost:5000
"""

# ============================================================================
# CONFIGURATION OPTIONS
# ============================================================================

CONFIGURATION = {
    'Debug Mode': {
        'Enabled by default': True,
        'Location': 'app.py line: app.run(debug=True)',
        'Note': 'Set to False for production'
    },
    'Port Configuration': {
        'Default': 5000,
        'Change to': 'app.run(debug=True, port=8000)',
        'Useful for': 'If port 5000 is already in use'
    },
    'Template Folder': {
        'Location': './templates',
        'Contains': 'index.html'
    },
    'Static Folder': {
        'Location': './static',
        'Contains': 'style.css, script.js'
    }
}

# ============================================================================
# ALGORITHM PARAMETERS (Customizable)
# ============================================================================

ALGORITHM_PARAMETERS = {
    'Emergency Exclusion Penalty': {
        'Current': 5000,
        'Location': 'schedule.py line: cost = 5000',
        'Effect': 'Higher = less likely to assign',
        'Range': '1000 - 10000'
    },
    'Priority Date Cost': {
        'Current': 'index * 10',
        'Location': 'schedule.py line: cost = person_info["priority_dates"].index(d) * 10',
        'Effect': 'Multiplier for priority preference',
        'Range': '1 - 100'
    },
    'Auto-Draft Penalty': {
        'Current': 200,
        'Location': 'schedule.py line: cost = 200',
        'Effect': 'Cost for non-preferred dates',
        'Range': '50 - 1000'
    }
}

# ============================================================================
# ENVIRONMENT VARIABLES (Optional)
# ============================================================================

ENVIRONMENT_VARIABLES = """
Optional environment variables you can set:

FLASK_ENV=development       # Enable debug mode
FLASK_DEBUG=1              # Enable auto-reload
FLASK_APP=app.py           # Specify Flask application

Example (Windows):
set FLASK_ENV=development
set FLASK_DEBUG=1
python app.py

Example (Linux/Mac):
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
"""

# ============================================================================
# DATABASE SETUP (For Future Enhancement)
# ============================================================================

DATABASE_SETUP = """
To add database support in the future:

1. Install SQLAlchemy:
   pip install flask-sqlalchemy

2. Add to app.py:
   from flask_sqlalchemy import SQLAlchemy
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedules.db'
   db = SQLAlchemy(app)

3. Define models for storing schedules
4. Modify API endpoints to use database persistence
"""

# ============================================================================
# SECURITY CONSIDERATIONS
# ============================================================================

SECURITY_CHECKLIST = """
Before deployment:

[ ] Disable debug mode: app.run(debug=False)
[ ] Use environment variables for secrets
[ ] Add CORS restrictions if serving from specific domain
[ ] Implement rate limiting on API endpoints
[ ] Add input validation on all form fields
[ ] Use HTTPS in production
[ ] Add authentication layer if multi-user
[ ] Validate file uploads if disk storage used
[ ] Set secure cookie attributes
[ ] Add CSRF protection
[ ] Implement logging and monitoring
"""

# ============================================================================
# PERFORMANCE OPTIMIZATION
# ============================================================================

PERFORMANCE_TIPS = """
For better performance:

1. Use production WSGI server (Gunicorn):
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app

2. Enable caching for static files:
   # Add to app configuration

3. Compress responses:
   pip install flask-compress

4. Use CDN for static assets in production

5. Enable browser caching in CSS/JS serving

6. Monitor and log slow queries

7. Use connection pooling for databases
"""

# ============================================================================
# TROUBLESHOOTING GUIDE
# ============================================================================

TROUBLESHOOTING = {
    'Port 5000 already in use': {
        'Error': 'Error: [WinError 10048]',
        'Solution': 'Change port in app.py or kill process using port 5000',
        'Command': 'lsof -i :5000  # Check process\nkill -9 <PID>  # Kill process'
    },
    'ModuleNotFoundError': {
        'Error': 'No module named flask',
        'Solution': 'Install dependencies',
        'Command': 'pip install -r requirements.txt'
    },
    'Template not found': {
        'Error': 'jinja2.exceptions.TemplateNotFound',
        'Solution': 'Ensure templates folder exists and index.html is present',
        'Check': 'ls -la templates/'
    },
    'Static files not loading': {
        'Error': 'CSS/JS not loaded, 404 errors in console',
        'Solution': 'Check static folder and file paths',
        'Check': 'ls -la static/'
    },
    'Excel export fails': {
        'Error': 'ModuleNotFoundError: openpyxl',
        'Solution': 'Install openpyxl',
        'Command': 'pip install openpyxl'
    }
}

# ============================================================================
# DEPLOYMENT OPTIONS
# ============================================================================

DEPLOYMENT_OPTIONS = """
Development:
- Use built-in Flask server
- app.run(debug=True)
- Suitable for testing and development only

Production (Single Server):
- Use Gunicorn + Nginx
- Set debug=False
- Use environment variables for config

Production (Scalable):
- Use Docker containers
- Deploy to cloud (AWS, Google Cloud, Azure)
- Use load balancer
- Implement caching layer (Redis)
- Use RDS or MongoDB for persistence

Example Docker setup:
# Dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

# Build: docker build -t schedule-app .
# Run: docker run -p 5000:5000 schedule-app
"""

# ============================================================================
# MAINTENANCE & MONITORING
# ============================================================================

MAINTENANCE = """
Regular maintenance tasks:

Daily:
- Monitor error logs
- Check system performance
- Review user feedback

Weekly:
- Backup schedules/database
- Review access logs
- Update documentation

Monthly:
- Performance analysis
- Security audit
- Dependency updates
- User feedback implementation

Quarterly:
- Full system audit
- Performance optimization
- Feature requests evaluation
"""

# ============================================================================
# USEFUL COMMANDS
# ============================================================================

USEFUL_COMMANDS = {
    'Windows': {
        'Run app': 'python app.py',
        'Install deps': 'pip install -r requirements.txt',
        'Check port': 'netstat -ano | findstr :5000',
        'Kill process': 'taskkill /PID <PID> /F'
    },
    'Linux/Mac': {
        'Run app': 'python3 app.py',
        'Install deps': 'pip3 install -r requirements.txt',
        'Check port': 'lsof -i :5000',
        'Kill process': 'kill -9 <PID>'
    },
    'Python': {
        'Check version': 'python --version',
        'Virtual env': 'python -m venv venv',
        'Activate venv': 'source venv/bin/activate  # Linux/Mac',
        'Activate venv Windows': '.\\venv\\Scripts\\activate'
    }
}

# ============================================================================
# QUICK START REMINDER
# ============================================================================

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  Exam Invigilation Scheduling System - Configuration Guide    ║
    ╚════════════════════════════════════════════════════════════════╝
    
    Quick Start:
    1. pip install -r requirements.txt
    2. python app.py
    3. Open http://localhost:5000
    
    For detailed setup, see README.md and QUICK_START.md
    """)
