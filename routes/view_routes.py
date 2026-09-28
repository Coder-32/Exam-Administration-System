import logging
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from service.db import get_all_data

logger = logging.getLogger(__name__)

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
@login_required
def index():
    logger.info(f'Loading main scheduling dashboard for user: {current_user.username}')
    return render_template('index.html', username=current_user.username)

@views_bp.route('/register')
@login_required
def register():
    """Registration and management page for teachers, staff, and rooms"""
    data = get_all_data(current_user.id)
    return render_template('register.html', username=current_user.username, **data)
