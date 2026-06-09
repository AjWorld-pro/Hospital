from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import *
from utils.decorators import admin_required
from utils.helpers import log_activity, generate_bill_number, create_notification
from datetime import datetime, date

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    total_patients = Patient.query.count()
    total_doctors = Doctor.query.count()
    total_appointments = Appointment.query.count()
    total_departments = Department.query.count()
    emergency_cases = Appointment.query.filter_by(is_emergency=True, status='scheduled').count()
    total_bills = Billing.query.count()
    revenue = db.session.query(db.func.sum(Billing.total_amount)).filter_by(payment_status='paid').scalar() or 0
    pending_bills = Billing.query.filter_by(payment_status='unpaid').count()
    today_appointments = Appointment.query.filter(
        Appointment.appointment_date == date.today(),
        Appointment.status != 'cancelled'
    ).count()
    active_patients = Patient.query.filter_by(is_active=True).count()
    pending_triage = Triage.query.filter_by(status='pending').count()
    total_nurses = User.query.filter_by(role='nurse').count()

    recent_patients = Patient.query.order_by(Patient.id.desc()).limit(5).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
        total_patients=total_patients, total_doctors=total_doctors,
        total_appointments=total_appointments, total_departments=total_departments,
        emergency_cases=emergency_cases, total_bills=total_bills,
        revenue=revenue, pending_bills=pending_bills,
        today_appointments=today_appointments, active_patients=active_patients,
        pending_triage=pending_triage, total_nurses=total_nurses,
        recent_patients=recent_patients, recent_activities=recent_activities)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.role, User.name).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
        else:
            user = User(username=username, password=password, role=role, name=name, email=email, phone=phone)
            db.session.add(user)
            db.session.flush()
            if role == 'doctor':
                doctor = Doctor(user_id=user.id, department_id=1, specialization=request.form.get('specialization', 'General'))
                db.session.add(doctor)
            log_activity(current_user.id, 'Create User', 'User', user.id, f'Created {role}: {username}')
            db.session.commit()
            flash('User created successfully!', 'success')
            return redirect(url_for('admin.manage_users'))
    departments = Department.query.filter_by(is_active=True).all()
    return render_template('admin/create_user.html', departments=departments)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.email = request.form.get('email', user.email)
        user.phone = request.form.get('phone', user.phone)
        if request.form.get('password'):
            user.set_password(request.form.get('password'))
        log_activity(current_user.id, 'Edit User', 'User', user.id, f'Edited user: {user.username}')
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/toggle/<int:user_id>')
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate yourself.', 'danger')
        return redirect(url_for('admin.manage_users'))
    user.is_active_account = not user.is_active_account
    log_activity(current_user.id, 'Toggle User Status', 'User', user.id,
        f'{"Activated" if user.is_active_account else "Deactivated"} user: {user.username}')
    db.session.commit()
    flash(f'User {"activated" if user.is_active_account else "deactivated"} successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('admin.manage_users'))
    if user.is_admin:
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot delete the last admin account.', 'danger')
            return redirect(url_for('admin.manage_users'))
    username = user.username
    if user.doctor_profile:
        db.session.delete(user.doctor_profile)
    db.session.delete(user)
    log_activity(current_user.id, 'Delete User', 'User', user_id, f'Deleted user: {username}')
    db.session.commit()
    flash(f'User {username} deleted successfully.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/doctors')
@login_required
@admin_required
def manage_doctors():
    doctors = Doctor.query.all()
    return render_template('admin/doctors.html', doctors=doctors)

@admin_bp.route('/doctors/edit/<int:doc_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_doctor(doc_id):
    doctor = Doctor.query.get_or_404(doc_id)
    STANDARD_DEPARTMENTS = ['General Physician', 'Cardiology', 'Dermatology', 'Pediatrics', 'Gynecology', 'Orthopedics', 'Neurology', 'Psychiatry', 'Ophthalmology', 'ENT', 'Dentistry', 'Radiology', 'Anesthesiology', 'Pathology', 'Pulmonology', 'Gastroenterology', 'Nephrology', 'Oncology', 'Urology', 'Endocrinology', 'Rheumatology', 'Surgery']
    if request.method == 'POST':
        raw_dept = request.form.get('department_id', str(doctor.department_id))
        if raw_dept == '0':
            custom_name = request.form.get('custom_department', '').strip()
            existing = Department.query.filter_by(name=custom_name).first()
            dept_id = existing.id if existing else None
            if not existing and custom_name:
                dept = Department(name=custom_name, description='Custom department')
                db.session.add(dept)
                db.session.flush()
                dept_id = dept.id
        elif raw_dept.startswith('new_'):
            dept_name = raw_dept[4:]
            existing = Department.query.filter_by(name=dept_name).first()
            if existing:
                dept_id = existing.id
            else:
                dept = Department(name=dept_name, description='Standard department')
                db.session.add(dept)
                db.session.flush()
                dept_id = dept.id
        else:
            dept_id = int(raw_dept)
        doctor.department_id = dept_id or doctor.department_id
        doctor.specialization = request.form.get('specialization', doctor.specialization)
        doctor.qualifications = request.form.get('qualifications', doctor.qualifications)
        doctor.experience_years = int(request.form.get('experience_years', 0))
        doctor.consultation_fee = float(request.form.get('consultation_fee', 0))
        doctor.is_available = request.form.get('is_available') == 'on'
        log_activity(current_user.id, 'Edit Doctor', 'Doctor', doc_id, f'Updated doctor profile')
        db.session.commit()
        flash('Doctor updated successfully!', 'success')
        return redirect(url_for('admin.manage_doctors'))
    departments = Department.query.filter_by(is_active=True).all()
    existing_names = {d.name for d in departments}
    standard_departments = [d for d in STANDARD_DEPARTMENTS if d not in existing_names]
    return render_template('admin/edit_doctor.html', doctor=doctor, departments=departments, standard_departments=standard_departments)

@admin_bp.route('/patients/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register_patient():
    if request.method == 'POST':
        try:
            dob = datetime.strptime(request.form.get('date_of_birth'), '%Y-%m-%d').date()
        except:
            flash('Invalid date format.', 'danger')
            return render_template('receptionist/register_patient.html')
        patient = Patient(
            first_name=request.form.get('first_name', '').strip(),
            last_name=request.form.get('last_name', '').strip(),
            date_of_birth=dob,
            gender=request.form.get('gender'),
            blood_group=request.form.get('blood_group'),
            phone=request.form.get('phone', '').strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address'),
            city=request.form.get('city'),
            state=request.form.get('state'),
            zip_code=request.form.get('zip_code'),
            emergency_contact_name=request.form.get('emergency_contact_name'),
            emergency_contact_phone=request.form.get('emergency_contact_phone'),
            emergency_contact_relation=request.form.get('emergency_contact_relation'),
            allergies=', '.join(request.form.getlist('allergies')),
            chronic_conditions=', '.join(request.form.getlist('chronic_conditions')),
            current_medications=', '.join(request.form.getlist('current_medications')),
            past_surgeries=', '.join(request.form.getlist('past_surgeries')),
            family_medical_history=', '.join(request.form.getlist('family_medical_history')),
            insurance_provider=request.form.get('insurance_provider'),
            insurance_policy_number=request.form.get('insurance_policy_number'),
            created_by=current_user.id
        )
        db.session.add(patient)
        db.session.flush()
        triage = Triage(patient_id=patient.id, status='pending')
        db.session.add(triage)
        db.session.flush()
        nurses = User.query.filter_by(role='nurse').all()
        for nurse in nurses:
            create_notification(nurse.id, 'New Patient for Triage',
                f'Patient {patient.full_name} has been registered and needs triage.',
                'info', patient.id)
        log_activity(current_user.id, 'Register Patient', 'Patient', patient.id,
            f'Registered: {patient.full_name}')
        db.session.commit()
        flash(f'Patient {patient.full_name} registered successfully! Send to triage for vitals.', 'success')
        return redirect(url_for('admin.manage_patients'))
    return render_template('receptionist/register_patient.html')

@admin_bp.route('/patients')
@login_required
@admin_required
def manage_patients():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = Patient.query
    if search:
        query = query.filter(
            db.or_(Patient.first_name.ilike(f'%{search}%'),
                   Patient.last_name.ilike(f'%{search}%'),
                   Patient.phone.ilike(f'%{search}%'),
                   Patient.email.ilike(f'%{search}%'))
        )
    query = query.filter_by(is_active=True)
    patients = query.order_by(Patient.id.asc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/patients.html', patients=patients, search=search)

@admin_bp.route('/patients/view/<int:patient_id>')
@login_required
@admin_required
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).all()
    records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).all()
    bills = Billing.query.filter_by(patient_id=patient_id).order_by(Billing.created_at.desc()).all()
    triages = Triage.query.filter_by(patient_id=patient_id).order_by(Triage.id.desc()).all()
    return render_template('admin/view_patient.html', patient=patient,
        appointments=appointments, records=records, bills=bills, triages=triages)

@admin_bp.route('/patients/toggle-archive/<int:patient_id>')
@login_required
@admin_required
def toggle_patient_archive(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_active = not patient.is_active
    action = 'restored' if patient.is_active else 'archived'
    log_activity(current_user.id, f'{action.title()} Patient', 'Patient', patient_id,
        f'Patient: {patient.full_name}')
    db.session.commit()
    flash(f'Patient {patient.full_name} has been {action}.', 'success')
    return redirect(request.referrer or url_for('admin.manage_patients'))

@admin_bp.route('/patients/archived')
@login_required
@admin_required
def archived_patients():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = Patient.query.filter_by(is_active=False)
    if search:
        query = query.filter(
            db.or_(Patient.first_name.ilike(f'%{search}%'),
                   Patient.last_name.ilike(f'%{search}%'),
                   Patient.phone.ilike(f'%{search}%'))
        )
    patients = query.order_by(Patient.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/archived_patients.html', patients=patients, search=search)

@admin_bp.route('/patients/medical-history/<int:patient_id>')
@login_required
@admin_required
def patient_medical_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id, is_active=True).all()
    return render_template('admin/medical_history.html', patient=patient, records=records, prescriptions=prescriptions)

@admin_bp.route('/appointments')
@login_required
@admin_required
def manage_appointments():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Appointment.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    appointments = query.order_by(Appointment.appointment_date.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/appointments.html', appointments=appointments, status_filter=status_filter)

@admin_bp.route('/billing')
@login_required
@admin_required
def manage_billing():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Billing.query
    if status_filter:
        query = query.filter_by(payment_status=status_filter)
    bills = query.order_by(Billing.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/billing.html', bills=bills, status_filter=status_filter)

@admin_bp.route('/billing/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_bill():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id', type=int)
        bill = Billing(
            patient_id=patient_id,
            bill_number=generate_bill_number(),
            consultation_fee=float(request.form.get('consultation_fee', 0)),
            lab_charges=float(request.form.get('lab_charges', 0)),
            medication_charges=float(request.form.get('medication_charges', 0)),
            procedure_charges=float(request.form.get('procedure_charges', 0)),
            room_charges=float(request.form.get('room_charges', 0)),
            other_charges=float(request.form.get('other_charges', 0)),
            discount=float(request.form.get('discount', 0)),
            tax=float(request.form.get('tax', 0)),
            notes=request.form.get('notes'),
            created_by=current_user.id
        )
        item_names = request.form.getlist('item_name[]')
        item_types = request.form.getlist('item_type[]')
        item_qtys = request.form.getlist('item_qty[]')
        item_prices = request.form.getlist('item_price[]')
        for i in range(len(item_names)):
            name = item_names[i].strip()
            qty = int(item_qtys[i]) if i < len(item_qtys) else 1
            price = float(item_prices[i]) if i < len(item_prices) else 0
            if name and price > 0:
                item = BillingItem(
                    billing_id=bill.id, item_name=name,
                    item_type=item_types[i] if i < len(item_types) else 'other',
                    quantity=qty, unit_price=price, total_price=qty * price
                )
                db.session.add(item)
        bill.calculate_totals()
        db.session.add(bill)
        log_activity(current_user.id, 'Create Bill', 'Billing', bill.id)
        db.session.commit()
        flash('Bill created successfully! You can now record payment.', 'success')
        return redirect(url_for('admin.view_bill', bill_id=bill.id))
    patients = Patient.query.order_by(Patient.last_name).all()
    return render_template('admin/create_bill.html', patients=patients)

@admin_bp.route('/billing/view/<int:bill_id>')
@login_required
@admin_required
def view_bill(bill_id):
    bill = Billing.query.get_or_404(bill_id)
    return render_template('admin/view_bill.html', bill=bill)

@admin_bp.route('/billing/pay/<int:bill_id>', methods=['POST'])
@login_required
@admin_required
def pay_bill(bill_id):
    bill = Billing.query.get_or_404(bill_id)
    amount = float(request.form.get('amount', 0))
    bill.paid_amount += amount
    bill.payment_method = request.form.get('payment_method', 'cash')
    bill.calculate_totals()
    if bill.payment_status == 'paid':
        bill.payment_date = datetime.utcnow()
    log_activity(current_user.id, 'Payment Received', 'Billing', bill_id, f'Amount: {amount}')
    db.session.commit()
    flash('Payment recorded successfully!', 'success')
    return redirect(url_for('admin.manage_billing'))

@admin_bp.route('/departments')
@login_required
@admin_required
def manage_departments():
    departments = Department.query.all()
    return render_template('admin/departments.html', departments=departments)

@admin_bp.route('/departments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    if request.method == 'POST':
        dept = Department(
            name=request.form.get('name'),
            description=request.form.get('description'),
            location=request.form.get('location'),
            phone=request.form.get('phone')
        )
        db.session.add(dept)
        log_activity(current_user.id, 'Create Department', 'Department', dept.id, f'Created: {dept.name}')
        db.session.commit()
        flash('Department created successfully!', 'success')
        return redirect(url_for('admin.manage_departments'))
    return render_template('admin/create_department.html')

@admin_bp.route('/departments/edit/<int:dept_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    if request.method == 'POST':
        dept.name = request.form.get('name', dept.name)
        dept.description = request.form.get('description', dept.description)
        dept.location = request.form.get('location', dept.location)
        dept.phone = request.form.get('phone', dept.phone)
        log_activity(current_user.id, 'Edit Department', 'Department', dept_id)
        db.session.commit()
        flash('Department updated successfully!', 'success')
        return redirect(url_for('admin.manage_departments'))
    return render_template('admin/edit_department.html', dept=dept)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    report_type = request.args.get('type', 'daily')
    today = date.today()
    if report_type == 'daily':
        appointments = Appointment.query.filter(Appointment.appointment_date == today).count()
        revenue = db.session.query(db.func.sum(Billing.total_amount)).filter(
            db.func.date(Billing.payment_date) == today).scalar() or 0
        new_patients = Patient.query.filter(db.func.date(Patient.registration_date) == today).count()
    elif report_type == 'weekly':
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        appointments = Appointment.query.filter(Appointment.appointment_date >= week_ago).count()
        revenue = db.session.query(db.func.sum(Billing.total_amount)).filter(Billing.payment_date >= week_ago).scalar() or 0
        new_patients = Patient.query.filter(Patient.registration_date >= week_ago).count()
    else:
        month_start = today.replace(day=1)
        appointments = Appointment.query.filter(Appointment.appointment_date >= month_start).count()
        revenue = db.session.query(db.func.sum(Billing.total_amount)).filter(Billing.payment_date >= month_start).scalar() or 0
        new_patients = Patient.query.filter(Patient.registration_date >= month_start).count()
    return render_template('admin/reports.html', report_type=report_type,
        appointments=appointments, revenue=revenue, new_patients=new_patients)

@admin_bp.route('/activity-logs')
@login_required
@admin_required
def activity_logs():
    page = request.args.get('page', 1, type=int)
    logs = ActivityLog.query.order_by(ActivityLog.id.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/activity_logs.html', logs=logs)

@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    from datetime import timedelta
    days = int(request.args.get('days', 30))
    since = datetime.utcnow() - timedelta(days=days)
    appointments_data = db.session.query(
        db.func.date(Appointment.appointment_date).label('date'),
        db.func.count(Appointment.id).label('count')
    ).filter(Appointment.appointment_date >= since.date()).group_by(db.func.date(Appointment.appointment_date)).all()
    revenue_data = db.session.query(
        db.func.date(Billing.payment_date).label('date'),
        db.func.sum(Billing.total_amount).label('total')
    ).filter(Billing.payment_date >= since, Billing.payment_status == 'paid').group_by(db.func.date(Billing.payment_date)).all()
    return jsonify({
        'appointments': [{'date': str(a.date), 'count': a.count} for a in appointments_data],
        'revenue': [{'date': str(r.date), 'total': float(r.total)} for r in revenue_data],
        'total_patients': Patient.query.count(),
        'total_doctors': Doctor.query.count(),
        'total_appointments': Appointment.query.count()
    })

@admin_bp.route('/search')
@login_required
@admin_required
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return render_template('admin/search.html', results=None, query=q)
    patients = Patient.query.filter(
        db.or_(Patient.first_name.ilike(f'%{q}%'),
               Patient.last_name.ilike(f'%{q}%'),
               Patient.phone.ilike(f'%{q}%'),
               Patient.email.ilike(f'%{q}%'))
    ).limit(10).all()
    doctors = Doctor.query.join(User).filter(
        db.or_(User.name.ilike(f'%{q}%'),
               Doctor.specialization.ilike(f'%{q}%'))
    ).limit(10).all()
    return render_template('admin/search.html', results={'patients': patients, 'doctors': doctors}, query=q)
