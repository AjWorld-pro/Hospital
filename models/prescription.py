from datetime import datetime
from . import db

class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    medication_name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100))
    route = db.Column(db.String(50))
    instructions = db.Column(db.Text)
    refill_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    prescribed_date = db.Column(db.DateTime, default=datetime.utcnow)
    prescribed_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'patient_name': self.patient.full_name if self.patient else 'N/A',
            'doctor_name': self.doctor.user.name if self.doctor and self.doctor.user else 'N/A',
            'medication': self.medication_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'is_active': self.is_active,
            'prescribed_date': self.prescribed_date.isoformat() if self.prescribed_date else None
        }

    def __repr__(self):
        return f'<Prescription {self.medication_name}>'
