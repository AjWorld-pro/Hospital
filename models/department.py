from datetime import datetime
from . import db

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    head_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctors = db.relationship('Doctor', backref='department', lazy=True, foreign_keys='Doctor.department_id')
    appointments = db.relationship('Appointment', backref='department', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'location': self.location,
            'phone': self.phone,
            'doctor_count': len(self.doctors) if self.doctors else 0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Department {self.name}>'
