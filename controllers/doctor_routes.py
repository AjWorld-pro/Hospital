from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import *
from utils.decorators import role_required
from utils.helpers import log_activity, create_notification
from datetime import datetime, date
from sqlalchemy import case
import json

priority_order = case(
    (EmergencyQueue.priority == 'critical', 1),
    (EmergencyQueue.priority == 'high', 2),
    (EmergencyQueue.priority == 'medium', 3),
    (EmergencyQueue.priority == 'low', 4),
    else_=99
)

doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor_bp.route('/')
@login_required
@role_required('doctor')
def dashboard():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Doctor profile not found.', 'danger')
        return redirect(url_for('auth.logout'))
    today = date.today()
    today_appointments = Appointment.query.filter_by(doctor_id=doctor.id, appointment_date=today).order_by(Appointment.appointment_time).all()
    total_patients = db.session.query(db.func.count(db.distinct(Appointment.patient_id))).filter_by(doctor_id=doctor.id).scalar() or 0
    pending_appointments = Appointment.query.filter_by(doctor_id=doctor.id, status='scheduled').count()
    completed_today = Appointment.query.filter_by(doctor_id=doctor.id, appointment_date=today, status='completed').count()
    recent_patients = Patient.query.join(Appointment).filter(Appointment.doctor_id == doctor.id).order_by(Appointment.id.desc()).limit(5).all()
    triaged_patients = Triage.query.filter_by(assigned_doctor_id=doctor.id, status='completed').order_by(Triage.completed_time.desc()).limit(10).all()
    return render_template('doctor/dashboard.html', doctor=doctor,
        today_appointments=today_appointments, total_patients=total_patients,
        pending_appointments=pending_appointments, completed_today=completed_today,
        recent_patients=recent_patients, triaged_patients=triaged_patients)

@doctor_bp.route('/patients')
@login_required
@role_required('doctor')
def my_patients():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    search = request.args.get('search', '')
    appt_ids = [r[0] for r in db.session.query(Appointment.patient_id).filter_by(doctor_id=doctor.id).distinct().all()]
    triage_ids = [r[0] for r in db.session.query(Triage.patient_id).filter_by(assigned_doctor_id=doctor.id, status='completed').distinct().all()]
    all_ids = set(appt_ids + triage_ids)
    query = Patient.query.filter(Patient.id.in_(all_ids)) if all_ids else Patient.query.filter(db.text('0=1'))
    if search:
        query = query.filter(db.or_(
            Patient.first_name.ilike(f'%{search}%'),
            Patient.last_name.ilike(f'%{search}%'),
            Patient.phone.ilike(f'%{search}%')
        ))
    patients = query.order_by(Patient.last_name).all()
    return render_template('doctor/patients.html', patients=patients, search=search)

@doctor_bp.route('/patients/<int:patient_id>')
@login_required
@role_required('doctor')
def view_patient(patient_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(patient_id=patient_id, doctor_id=doctor.id).order_by(MedicalRecord.visit_date.desc()).all()
    appointments = Appointment.query.filter_by(patient_id=patient_id, doctor_id=doctor.id).order_by(Appointment.appointment_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id, doctor_id=doctor.id).order_by(Prescription.prescribed_date.desc()).all()
    triages = Triage.query.filter_by(patient_id=patient_id).order_by(Triage.id.desc()).all()
    return render_template('doctor/view_patient.html', patient=patient,
        records=records, appointments=appointments, prescriptions=prescriptions, triages=triages)

@doctor_bp.route('/appointments')
@login_required
@role_required('doctor')
def appointments():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    status_filter = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    query = Appointment.query.filter_by(doctor_id=doctor.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date == filter_date)
        except:
            pass
    appointments = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time).all()
    return render_template('doctor/appointments.html', appointments=appointments, status_filter=status_filter, date_filter=date_filter)

@doctor_bp.route('/appointments/update-status/<int:appt_id>', methods=['POST'])
@login_required
@role_required('doctor')
def update_appointment_status(appt_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    appointment = Appointment.query.get_or_404(appt_id)
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('doctor.appointments'))
    new_status = request.form.get('status')
    if new_status in Appointment.STATUS_CHOICES:
        appointment.status = new_status
        if new_status == 'completed':
            patient = Patient.query.get(appointment.patient_id)
            if patient:
                patient.last_visit = datetime.utcnow()
        log_activity(current_user.id, 'Update Appointment Status', 'Appointment', appt_id, f'Status: {new_status}')
        db.session.commit()
        flash(f'Appointment marked as {new_status}!', 'success')
    return redirect(url_for('doctor.appointments'))

@doctor_bp.route('/medical-records/create/<int:patient_id>', defaults={'appointment_id': None}, methods=['GET', 'POST'])
@doctor_bp.route('/medical-records/create/<int:patient_id>/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def create_medical_record(patient_id, appointment_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        record = MedicalRecord(
            patient_id=patient_id, doctor_id=doctor.id, appointment_id=appointment_id,
            chief_complaint=request.form.get('chief_complaint'),
            symptoms=request.form.get('symptoms'),
            diagnosis=request.form.get('diagnosis'),
            treatment_plan=request.form.get('treatment_plan'),
            medications_prescribed=request.form.get('medications_prescribed'),
            lab_tests_ordered=request.form.get('lab_tests_ordered'),
            lab_results=request.form.get('lab_results'),
            vital_signs=request.form.get('vital_signs'),
            notes=request.form.get('notes'),
            follow_up_date=datetime.strptime(request.form.get('follow_up_date'), '%Y-%m-%d').date() if request.form.get('follow_up_date') else None
        )
        db.session.add(record)
        if appointment_id:
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                appointment.status = 'completed'
                patient.last_visit = datetime.utcnow()
        log_activity(current_user.id, 'Create Medical Record', 'MedicalRecord', record.id, f'Patient: {patient.full_name}')
        db.session.commit()
        flash('Medical record created successfully!', 'success')
        return redirect(url_for('doctor.view_patient', patient_id=patient_id))
    return render_template('doctor/create_medical_record.html', patient=patient, appointment_id=appointment_id)

@doctor_bp.route('/medical-records/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def edit_medical_record(record_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    record = MedicalRecord.query.get_or_404(record_id)
    if record.doctor_id != doctor.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('doctor.dashboard'))
    if request.method == 'POST':
        record.chief_complaint = request.form.get('chief_complaint', record.chief_complaint)
        record.symptoms = request.form.get('symptoms', record.symptoms)
        record.diagnosis = request.form.get('diagnosis', record.diagnosis)
        record.treatment_plan = request.form.get('treatment_plan', record.treatment_plan)
        record.medications_prescribed = request.form.get('medications_prescribed', record.medications_prescribed)
        record.lab_results = request.form.get('lab_results', record.lab_results)
        record.notes = request.form.get('notes', record.notes)
        record.is_discharged = request.form.get('is_discharged') == 'on'
        record.discharge_summary = request.form.get('discharge_summary') if record.is_discharged else None
        if request.form.get('follow_up_date'):
            record.follow_up_date = datetime.strptime(request.form.get('follow_up_date'), '%Y-%m-%d').date()
        log_activity(current_user.id, 'Edit Medical Record', 'MedicalRecord', record_id)
        db.session.commit()
        flash('Medical record updated!', 'success')
        return redirect(url_for('doctor.view_patient', patient_id=record.patient_id))
    return render_template('doctor/edit_medical_record.html', record=record)

@doctor_bp.route('/prescribe/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def prescribe(patient_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        prescription = Prescription(
            patient_id=patient_id, doctor_id=doctor.id,
            medication_name=request.form.get('medication_name'),
            dosage=request.form.get('dosage'),
            frequency=request.form.get('frequency'),
            duration=request.form.get('duration'),
            route=request.form.get('route'),
            instructions=request.form.get('instructions'),
            refill_count=int(request.form.get('refill_count', 0)),
            prescribed_by=current_user.id
        )
        db.session.add(prescription)
        log_activity(current_user.id, 'Create Prescription', 'Prescription', prescription.id, f'Patient: {patient.full_name}')
        db.session.commit()
        flash('Prescription added successfully!', 'success')
        return redirect(url_for('doctor.view_patient', patient_id=patient_id))
    return render_template('doctor/prescribe.html', patient=patient)

@doctor_bp.route('/discharge/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
def discharge_patient(patient_id):
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        record = MedicalRecord(
            patient_id=patient_id, doctor_id=doctor.id,
            diagnosis=request.form.get('diagnosis', ''),
            treatment_plan=request.form.get('treatment_plan'),
            notes=request.form.get('notes'),
            is_discharged=True,
            discharge_summary=request.form.get('discharge_summary')
        )
        db.session.add(record)
        Patient.query.get(patient_id).is_active = False
        log_activity(current_user.id, 'Discharge Patient', 'Patient', patient_id,
            f'Patient: {patient.full_name}')
        db.session.commit()
        flash('Patient discharged successfully!', 'success')
        return redirect(url_for('doctor.my_patients'))
    return render_template('doctor/discharge.html', patient=patient)

@doctor_bp.route('/emergency-queue')
@login_required
@role_required('doctor')
def emergency_queue():
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    queue = EmergencyQueue.query.filter(
        EmergencyQueue.status.in_(['waiting', 'triage']),
        db.or_(EmergencyQueue.assigned_doctor_id == doctor.id, EmergencyQueue.assigned_doctor_id == None)
    ).order_by(priority_order, EmergencyQueue.arrival_time).all()
    active_patients = EmergencyQueue.query.filter_by(assigned_doctor_id=doctor.id, status='with_doctor').all()
    return render_template('doctor/emergency_queue.html', queue=queue, active_patients=active_patients)

@doctor_bp.route('/emergency-queue/attend/<int:queue_id>')
@login_required
@role_required('doctor')
def attend_emergency(queue_id):
    entry = EmergencyQueue.query.get_or_404(queue_id)
    entry.status = 'with_doctor'
    entry.assigned_doctor_id = Doctor.query.filter_by(user_id=current_user.id).first().id
    entry.seen_time = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('doctor.emergency_queue'))

@doctor_bp.route('/medical-history/<int:patient_id>')
@login_required
@role_required('doctor')
def medical_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id, is_active=True).all()
    return render_template('doctor/medical_history.html', patient=patient, records=records, prescriptions=prescriptions)
