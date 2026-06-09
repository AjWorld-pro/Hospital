from datetime import datetime
from . import db

class Triage(db.Model):
    __tablename__ = 'triages'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    respiratory_rate = db.Column(db.Integer)
    oxygen_saturation = db.Column(db.Integer)
    chief_complaint = db.Column(db.Text)
    assessment = db.Column(db.Text)
    pain_level = db.Column(db.Integer)
    priority = db.Column(db.String(20), default='medium')
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    triage_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)

    patient = db.relationship('Patient', backref=db.backref('triages', lazy=True))
    nurse = db.relationship('User', backref=db.backref('triages', lazy=True), foreign_keys=[nurse_id])
    assigned_doctor = db.relationship('Doctor', backref=db.backref('triages', lazy=True), foreign_keys=[assigned_doctor_id])

    @property
    def bmi(self):
        if self.weight and self.height and self.height > 0:
            height_m = self.height / 100
            return round(self.weight / (height_m * height_m), 1)
        return None

    def __repr__(self):
        return f'<Triage {self.patient_id} ({self.status})>'
