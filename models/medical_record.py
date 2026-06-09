from datetime import datetime
from . import db

class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    chief_complaint = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    diagnosis = db.Column(db.Text, nullable=False)
    treatment_plan = db.Column(db.Text)
    medications_prescribed = db.Column(db.Text)
    lab_tests_ordered = db.Column(db.Text)
    lab_results = db.Column(db.Text)
    vital_signs = db.Column(db.Text)
    notes = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    is_discharged = db.Column(db.Boolean, default=False)
    discharge_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else 'N/A',
            'doctor_name': self.doctor.user.name if self.doctor and self.doctor.user else 'N/A',
            'diagnosis': self.diagnosis,
            'symptoms': self.symptoms,
            'treatment_plan': self.treatment_plan,
            'visit_date': self.visit_date.isoformat() if self.visit_date else None,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'is_discharged': self.is_discharged
        }

    def __repr__(self):
        return f'<MedicalRecord {self.id} - Patient {self.patient_id}>'
