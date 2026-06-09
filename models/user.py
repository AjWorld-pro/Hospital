from datetime import datetime
from flask_login import UserMixin
from . import db, bcrypt

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    is_active_account = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    doctor_profile = db.relationship('Doctor', backref='user', uselist=False, lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, foreign_keys='Notification.user_id')
    activities = db.relationship('ActivityLog', backref='user', lazy=True)

    ROLES = {'admin', 'doctor', 'receptionist', 'nurse'}

    def __init__(self, username, password, role, name, email=None, phone=None):
        self.username = username
        self.set_password(password)
        if role in self.ROLES:
            self.role = role
        else:
            raise ValueError(f"Invalid role. Must be one of: {self.ROLES}")
        self.name = name
        self.email = email
        self.phone = phone

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_doctor(self):
        return self.role == 'doctor'

    @property
    def is_receptionist(self):
        return self.role == 'receptionist'

    @property
    def is_nurse(self):
        return self.role == 'nurse'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'is_active': self.is_active_account,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
