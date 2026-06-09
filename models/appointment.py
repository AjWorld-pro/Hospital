from datetime import datetime
from . import db

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10))
    status = db.Column(db.String(20), default='scheduled')
    priority = db.Column(db.String(20), default='normal')
    reason = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    notes = db.Column(db.Text)
    is_emergency = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    STATUS_CHOICES = ['scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show']
    PRIORITY_CHOICES = ['low', 'normal', 'medium', 'high', 'critical']

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else 'N/A',
            'doctor_id': self.doctor_id,
            'doctor_name': self.doctor.user.name if self.doctor and self.doctor.user else 'N/A',
            'department': self.department.name if self.department else 'N/A',
            'date': self.appointment_date.isoformat() if self.appointment_date else None,
            'time': self.appointment_time,
            'status': self.status,
            'priority': self.priority,
            'reason': self.reason,
            'is_emergency': self.is_emergency
        }

    def __repr__(self):
        return f'<Appointment {self.id} - {self.status}>'
