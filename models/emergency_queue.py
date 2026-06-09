from datetime import datetime
from . import db

class EmergencyQueue(db.Model):
    __tablename__ = 'emergency_queue'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='waiting')
    complaint = db.Column(db.Text)
    triage_notes = db.Column(db.Text)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    arrival_time = db.Column(db.DateTime, default=datetime.utcnow)
    triage_time = db.Column(db.DateTime)
    seen_time = db.Column(db.DateTime)
    completed_time = db.Column(db.DateTime)
    waiting_number = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    PRIORITY_LEVELS = {'critical': 1, 'high': 2, 'medium': 3, 'low': 4}
    STATUS_CHOICES = ['waiting', 'triage', 'with_doctor', 'completed', 'cancelled']

    @property
    def priority_level(self):
        return self.PRIORITY_LEVELS.get(self.priority, 99)

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.full_name if self.patient else 'N/A',
            'priority': self.priority,
            'priority_level': self.priority_level,
            'status': self.status,
            'complaint': self.complaint,
            'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
            'waiting_number': self.waiting_number,
            'waiting_time': self.get_waiting_time()
        }

    def get_waiting_time(self):
        if self.arrival_time:
            delta = datetime.utcnow() - self.arrival_time
            minutes = int(delta.total_seconds() / 60)
            if minutes < 60:
                return f"{minutes}m"
            return f"{minutes // 60}h {minutes % 60}m"
        return "N/A"

    def __repr__(self):
        return f'<EmergencyQueue {self.waiting_number} - {self.priority}>'
