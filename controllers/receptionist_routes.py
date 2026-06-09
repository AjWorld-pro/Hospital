from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import *
from utils.decorators import role_required
from utils.helpers import log_activity, create_notification, generate_waiting_number
from datetime import datetime, date
from sqlalchemy import case

priority_order = case(
    (EmergencyQueue.priority == 'critical', 1),
    (EmergencyQueue.priority == 'high', 2),
    (EmergencyQueue.priority == 'medium', 3),
    (EmergencyQueue.priority == 'low', 4),
    else_=99
)

receptionist_bp = Blueprint('receptionist', __name__, url_prefix='/receptionist')

@receptionist_bp.route('/')
@login_required
@role_required('receptionist')
def dashboard():
    today = date.today()
    today_appointments = Appointment.query.filter(
        Appointment.appointment_date == today,
        Appointment.status != 'cancelled'
    ).count()
    total_patients = Patient.query.count()
    emergency_queue = EmergencyQueue.query.filter(EmergencyQueue.status.in_(['waiting', 'triage'])).count()
    pending_appointments = Appointment.query.filter_by(status='scheduled').count()
    recent_patients = Patient.query.order_by(Patient.id.desc()).limit(5).all()
    today_schedule = Appointment.query.filter_by(appointment_date=today).order_by(Appointment.appointment_time).limit(10).all()
    queue = EmergencyQueue.query.filter(EmergencyQueue.status.in_(['waiting', 'triage'])).order_by(priority_order, EmergencyQueue.arrival_time).all()
    pending_triage = Triage.query.filter_by(status='pending').count()
    return render_template('receptionist/dashboard.html',
        today_appointments=today_appointments, total_patients=total_patients,
        emergency_queue=emergency_queue, pending_appointments=pending_appointments,
        recent_patients=recent_patients, today_schedule=today_schedule, queue=queue,
        pending_triage=pending_triage)

@receptionist_bp.route('/patients/register', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
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
        return redirect(url_for('receptionist.patients'))
    return render_template('receptionist/register_patient.html')

@receptionist_bp.route('/patients')
@login_required
@role_required('receptionist')
def patients():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    query = Patient.query
    if search:
        query = query.filter(db.or_(
            Patient.first_name.ilike(f'%{search}%'),
            Patient.last_name.ilike(f'%{search}%'),
            Patient.phone.ilike(f'%{search}%'),
            Patient.email.ilike(f'%{search}%')
        ))
    patients = query.order_by(Patient.id.asc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('receptionist/patients.html', patients=patients, search=search)

@receptionist_bp.route('/medical-history/<int:patient_id>')
@login_required
@role_required('receptionist')
def medical_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id, is_active=True).all()
    return render_template('receptionist/medical_history.html', patient=patient, records=records, prescriptions=prescriptions)

@receptionist_bp.route('/patients/<int:patient_id>')
@login_required
@role_required('receptionist')
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).limit(10).all()
    bills = Billing.query.filter_by(patient_id=patient_id).order_by(Billing.created_at.desc()).limit(5).all()
    triages = Triage.query.filter_by(patient_id=patient_id).order_by(Triage.id.desc()).all()
    return render_template('receptionist/view_patient.html', patient=patient,
        appointments=appointments, bills=bills, triages=triages)

@receptionist_bp.route('/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('receptionist')
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.first_name = request.form.get('first_name', patient.first_name)
        patient.last_name = request.form.get('last_name', patient.last_name)
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            try:
                patient.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        patient.phone = request.form.get('phone', patient.phone)
        patient.email = request.form.get('email', patient.email)
        patient.address = request.form.get('address', patient.address)
        patient.city = request.form.get('city', patient.city)
        patient.state = request.form.get('state', patient.state)
        patient.zip_code = request.form.get('zip_code', patient.zip_code)
        patient.emergency_contact_name = request.form.get('emergency_contact_name', patient.emergency_contact_name)
        patient.emergency_contact_phone = request.form.get('emergency_contact_phone', patient.emergency_contact_phone)
        patient.blood_group = request.form.get('blood_group', patient.blood_group)
        patient.allergies = ', '.join(request.form.getlist('allergies')) or patient.allergies
        patient.chronic_conditions = ', '.join(request.form.getlist('chronic_conditions')) or patient.chronic_conditions
        patient.current_medications = ', '.join(request.form.getlist('current_medications')) or patient.current_medications
        patient.past_surgeries = ', '.join(request.form.getlist('past_surgeries')) or patient.past_surgeries
        patient.family_medical_history = ', '.join(request.form.getlist('family_medical_history')) or patient.family_medical_history
        patient.insurance_provider = request.form.get('insurance_provider', patient.insurance_provider)
        patient.insurance_policy_number = request.form.get('insurance_policy_number', patient.insurance_policy_number)
        log_activity(current_user.id, 'Edit Patient', 'Patient', patient_id)
        db.session.commit()
        flash('Patient information updated!', 'success')
        return redirect(url_for('receptionist.view_patient', patient_id=patient_id))
    return render_template('receptionist/edit_patient.html', patient=patient)

@receptionist_bp.route('/appointments/create', methods=['GET', 'POST'])
@login_required
@role_required('nurse', 'admin')
def create_appointment():
    if request.method == 'POST':
        patient_id = request.form.get('patient_id', type=int)
        doctor_id = request.form.get('doctor_id', type=int)
        appointment_date = datetime.strptime(request.form.get('appointment_date'), '%Y-%m-%d').date()
        appointment_time = request.form.get('appointment_time')
        doctor = Doctor.query.get(doctor_id)
        appointment = Appointment(
            patient_id=patient_id, doctor_id=doctor_id,
            department_id=doctor.department_id if doctor else 1,
            appointment_date=appointment_date, appointment_time=appointment_time,
            reason=request.form.get('reason'),
            symptoms=request.form.get('symptoms'),
            is_emergency=request.form.get('is_emergency') == 'on',
            priority='critical' if request.form.get('is_emergency') == 'on' else 'normal',
            created_by=current_user.id
        )
        db.session.add(appointment)
        db.session.flush()
        log_activity(current_user.id, 'Create Appointment', 'Appointment', appointment.id,
            f'Patient ID: {patient_id}, Doctor ID: {doctor_id}')
        if appointment.is_emergency:
            queue = EmergencyQueue(
                patient_id=patient_id, priority='critical',
                complaint=request.form.get('reason'),
                waiting_number=generate_waiting_number(),
                created_by=current_user.id
            )
            db.session.add(queue)
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                create_notification(admin.id, 'Emergency Case', f'New emergency patient registered',
                    'emergency', patient_id)
        db.session.commit()
        flash('Appointment created successfully!', 'success')
        return redirect(url_for('receptionist.appointments'))
    today = date.today()
    patients = Patient.query.filter_by(is_active=True).order_by(Patient.first_name).all()
    doctors = Doctor.query.filter_by(is_available=True).all()
    selected_patient_id = request.args.get('patient_id', type=int)
    selected_doctor_id = request.args.get('doctor_id', type=int)
    return render_template('receptionist/create_appointment.html',
        patients=patients, doctors=doctors, today=today,
        selected_patient_id=selected_patient_id,
        selected_doctor_id=selected_doctor_id)

@receptionist_bp.route('/appointments')
@login_required
@role_required('receptionist')
def appointments():
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', str(date.today()))
    query = Appointment.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    try:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter(Appointment.appointment_date == filter_date)
    except:
        pass
    appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time).all()
    return render_template('receptionist/appointments.html', appointments=appointments,
        status_filter=status_filter, date_filter=date_filter)

@receptionist_bp.route('/appointments/cancel/<int:appt_id>', methods=['POST'])
@login_required
@role_required('receptionist')
def cancel_appointment(appt_id):
    appointment = Appointment.query.get_or_404(appt_id)
    appointment.status = 'cancelled'
    appointment.notes = request.form.get('reason', appointment.notes or '')
    log_activity(current_user.id, 'Cancel Appointment', 'Appointment', appt_id,
        f'Cancelled appointment for patient {appointment.patient_id}')
    db.session.commit()
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('receptionist.appointments'))

@receptionist_bp.route('/emergency-queue')
@login_required
@role_required('receptionist')
def emergency_queue():
    queue = EmergencyQueue.query.filter(
        EmergencyQueue.status.in_(['waiting', 'triage'])
    ).order_by(priority_order, EmergencyQueue.arrival_time).all()
    history = EmergencyQueue.query.filter(
        EmergencyQueue.status.in_(['completed', 'with_doctor'])
    ).order_by(EmergencyQueue.arrival_time.desc()).limit(20).all()
    patients = Patient.query.filter_by(is_active=True).all()
    return render_template('receptionist/emergency_queue.html', queue=queue, history=history, patients=patients)

@receptionist_bp.route('/emergency-queue/add', methods=['POST'])
@login_required
@role_required('receptionist')
def add_to_queue():
    patient_id = request.form.get('patient_id', type=int)
    priority = request.form.get('priority', 'medium')
    complaint = request.form.get('complaint', '')
    entry = EmergencyQueue(
        patient_id=patient_id, priority=priority,
        complaint=complaint, waiting_number=generate_waiting_number(),
        created_by=current_user.id
    )
    db.session.add(entry)
    log_activity(current_user.id, 'Add to Emergency Queue', 'EmergencyQueue', entry.id,
        f'Patient ID: {patient_id}, Priority: {priority}')
    if priority == 'critical':
        admins = User.query.filter_by(role='admin').all()
        patient = Patient.query.get(patient_id)
        for admin in admins:
            create_notification(admin.id, 'Critical Emergency',
                f'Critical patient: {patient.full_name if patient else "Unknown"}',
                'emergency', patient_id)
    db.session.commit()
    flash('Added to emergency queue.', 'success')
    return redirect(url_for('receptionist.emergency_queue'))

@receptionist_bp.route('/get-doctors-by-department')
@login_required
@role_required('receptionist')
def get_doctors_by_department():
    department_id = request.args.get('department_id', type=int)
    doctors = Doctor.query.filter_by(department_id=department_id, is_available=True).all()
    return jsonify([{
        'id': d.id, 'name': d.user.name,
        'specialization': d.specialization, 'fee': d.consultation_fee
    } for d in doctors])

@receptionist_bp.route('/get-available-slots')
@login_required
@role_required('receptionist')
def get_available_slots():
    doctor_id = request.args.get('doctor_id', type=int)
    appt_date = request.args.get('date', '')
    if not doctor_id or not appt_date:
        return jsonify([])
    try:
        appt_date = datetime.strptime(appt_date, '%Y-%m-%d').date()
    except:
        return jsonify([])
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify([])
    booked = [a.appointment_time for a in Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=appt_date).filter(Appointment.status != 'cancelled').all()]
    slots = []
    start_h, start_m = (9, 0)
    end_h, end_m = (17, 0)
    if doctor.available_time_start:
        parts = doctor.available_time_start.split(':')
        start_h, start_m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    if doctor.available_time_end:
        parts = doctor.available_time_end.split(':')
        end_h, end_m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    current_h, current_m = start_h, start_m
    while current_h < end_h or (current_h == end_h and current_m < end_m):
        time_str = f"{current_h:02d}:{current_m:02d}"
        if time_str not in booked:
            slots.append(time_str)
        current_m += 30
        if current_m >= 60:
            current_h += 1
            current_m = 0
    return jsonify(slots)
