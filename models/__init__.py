from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

from .user import User
from .patient import Patient
from .doctor import Doctor
from .department import Department
from .appointment import Appointment
from .medical_record import MedicalRecord
from .billing import Billing, BillingItem
from .prescription import Prescription
from .emergency_queue import EmergencyQueue
from .notification import Notification
from .activity_log import ActivityLog
from .triage import Triage

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
