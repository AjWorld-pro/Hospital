from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, Doctor, Department, db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect_to_dashboard(current_user.role)
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.is_active_account:
                flash('This account has been deactivated.', 'danger')
                return render_template('login.html')
            login_user(user, remember=request.form.get('remember'))
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect_to_dashboard(user.role)
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect_to_dashboard(current_user.role)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', '')
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([name, username, role, password]):
            flash('All required fields must be filled.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('register.html')
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        user = User(username=username, password=password, role=role, name=name, email=email or None)
        db.session.add(user)
        db.session.flush()

        if role == 'doctor':
            dept = Department.query.first()
            spec = request.form.get('specialization', 'General Physician')
            doctor = Doctor(user_id=user.id, department_id=dept.id if dept else 1, specialization=spec)
            db.session.add(doctor)

        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/notifications')
@login_required
def notifications():
    from models import Notification
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).paginate(page=page, per_page=20, error_out=False)
    unread_ids = [n.id for n in notifs.items if not n.is_read]
    if unread_ids:
        Notification.query.filter(Notification.id.in_(unread_ids)).update({'is_read': True}, synchronize_session=False)
        db.session.commit()
    return render_template('notifications.html', notifications=notifs)

@auth_bp.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html'), 403

def redirect_to_dashboard(role):
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor.dashboard'))
    elif role == 'receptionist':
        return redirect(url_for('receptionist.dashboard'))
    elif role == 'nurse':
        return redirect(url_for('nurse.dashboard'))
    return redirect(url_for('auth.login'))
