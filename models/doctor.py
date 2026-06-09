from datetime import datetime
from . import db

class Doctor(db.Model):
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    license_number = db.Column(db.String(50), unique=True)
    specialization = db.Column(db.String(100), nullable=False)
    qualifications = db.Column(db.Text)
    experience_years = db.Column(db.Integer, default=0)
    consultation_fee = db.Column(db.Float, default=0.0)
    available_days = db.Column(db.String(200))
    available_time_start = db.Column(db.String(10))
    available_time_end = db.Column(db.String(10))
    max_patients_per_day = db.Column(db.Integer, default=20)
    is_available = db.Column(db.Boolean, default=True)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship('Appointment', backref='doctor', lazy=True, foreign_keys='Appointment.doctor_id')
    medical_records = db.relationship('MedicalRecord', backref='doctor', lazy=True)
    prescriptions = db.relationship('Prescription', backref='doctor', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.user.name if self.user else 'N/A',
            'email': self.user.email if self.user else 'N/A',
            'phone': self.user.phone if self.user else 'N/A',
            'department': self.department.name if self.department else 'N/A',
            'department_id': self.department_id,
            'specialization': self.specialization,
            'qualifications': self.qualifications,
            'experience_years': self.experience_years,
            'consultation_fee': self.consultation_fee,
            'is_available': self.is_available,
            'available_days': self.available_days
        }

    def __repr__(self):
        return f'<Doctor {self.specialization}>'
