from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import *
from utils.decorators import role_required
from utils.helpers import log_activity, create_notification, generate_waiting_number
from datetime import datetime, date

nurse_bp = Blueprint('nurse', __name__, url_prefix='/nurse')

@nurse_bp.route('/')
@login_required
@role_required('nurse')
def dashboard():
    today = date.today()
    pending_triage = Triage.query.filter_by(status='pending').count()
    completed_today = Triage.query.filter(
        Triage.status == 'completed',
        db.func.date(Triage.completed_time) == today
    ).count()
    total_triaged_today = Triage.query.filter(
        db.func.date(Triage.created_at) == today
    ).count()
    recent_triages = Triage.query.order_by(Triage.id.desc()).limit(5).all()
    return render_template('nurse/dashboard.html',
        pending_triage=pending_triage, completed_today=completed_today,
        total_triaged_today=total_triaged_today, recent_triages=recent_triages)

@nurse_bp.route('/triage-queue')
@login_required
@role_required('nurse')
def triage_queue():
    pending = Triage.query.filter_by(status='pending').order_by(Triage.created_at).all()
    today = date.today()
    completed = Triage.query.filter(
        Triage.status == 'completed',
        db.func.date(Triage.completed_time) == today
    ).order_by(Triage.completed_time.desc()).all()
    return render_template('nurse/triage_queue.html', pending=pending, completed=completed)

@nurse_bp.route('/triage/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@role_required('nurse')
def perform_triage(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    existing = Triage.query.filter_by(patient_id=patient_id, status='pending').first()
    if request.method == 'POST':
        try:
            if not existing:
                existing = Triage(patient_id=patient_id)
                db.session.add(existing)
                db.session.flush()
            existing.nurse_id = current_user.id
            existing.blood_pressure_systolic = request.form.get('bp_systolic', type=int)
            existing.blood_pressure_diastolic = request.form.get('bp_diastolic', type=int)
            existing.heart_rate = request.form.get('heart_rate', type=int)
            existing.temperature = request.form.get('temperature', type=float)
            existing.weight = request.form.get('weight', type=float)
            existing.height = request.form.get('height', type=float)
            existing.respiratory_rate = request.form.get('respiratory_rate', type=int)
            existing.oxygen_saturation = request.form.get('oxygen_saturation', type=int)
            existing.chief_complaint = request.form.get('chief_complaint')
            existing.assessment = request.form.get('assessment')
            existing.pain_level = request.form.get('pain_level', type=int)
            existing.priority = request.form.get('priority', 'medium')
            existing.assigned_doctor_id = request.form.get('assigned_doctor_id', type=int)
            existing.status = 'completed'
            existing.triage_time = datetime.utcnow()
            existing.completed_time = datetime.utcnow()
            log_activity(current_user.id, 'Complete Triage', 'Triage', existing.id,
                f'Triaged: {patient.full_name}, Priority: {existing.priority}')
            if existing.assigned_doctor_id:
                doctor = Doctor.query.get(existing.assigned_doctor_id)
                if doctor:
                    create_notification(doctor.user_id, 'New Patient Assigned',
                        f'Patient {patient.full_name} has been triaged and assigned to you (Priority: {existing.priority}).',
                        'info', patient_id)
            db.session.commit()
            flash(f'Triage completed for {patient.full_name}. Patient added to {existing.assigned_doctor.user.name if existing.assigned_doctor else "doctor"}\'s queue.', 'success')
            return redirect(url_for('nurse.triage_queue'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    doctors = Doctor.query.filter_by(is_available=True).all()
    return render_template('nurse/triage_form.html', patient=patient, triage=existing, doctors=doctors)

@nurse_bp.route('/patients')
@login_required
@role_required('nurse')
def patients():
    search = request.args.get('search', '')
    query = Patient.query
    if search:
        query = query.filter(db.or_(
            Patient.first_name.ilike(f'%{search}%'),
            Patient.last_name.ilike(f'%{search}%'),
            Patient.phone.ilike(f'%{search}%')
        ))
    patients = query.order_by(Patient.id.desc()).all()
    return render_template('nurse/patients.html', patients=patients, search=search)

@nurse_bp.route('/patients/<int:patient_id>')
@login_required
@role_required('nurse')
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    triages = Triage.query.filter_by(patient_id=patient_id).order_by(Triage.id.desc()).all()
    return render_template('nurse/view_patient.html', patient=patient, triages=triages)

@nurse_bp.route('/medical-history/<int:patient_id>')
@login_required
@role_required('nurse')
def medical_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).all()
    prescriptions = Prescription.query.filter_by(patient_id=patient_id, is_active=True).all()
    return render_template('nurse/medical_history.html', patient=patient, records=records, prescriptions=prescriptions)
