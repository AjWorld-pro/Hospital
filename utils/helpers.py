import re
from datetime import datetime, date
from models import ActivityLog, Notification, db

def log_activity(user_id, action, entity_type=None, entity_id=None, details=None, ip_address=None):
    log = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address
    )
    db.session.add(log)
    db.session.commit()

def create_notification(user_id, title, message, notification_type='info', related_id=None, is_global=False):
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=related_id,
        is_global=is_global
    )
    db.session.add(notif)
    db.session.commit()
    return notif

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone) is not None

def calculate_age(birth_date):
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def generate_bill_number():
    from models.billing import Billing
    last = Billing.query.order_by(Billing.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"BILL-{datetime.utcnow().strftime('%Y%m%d')}-{num:04d}"

def generate_waiting_number():
    from models.emergency_queue import EmergencyQueue
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    count = EmergencyQueue.query.filter(EmergencyQueue.arrival_time >= today_start).count()
    return count + 1

class PriorityQueue:
    def __init__(self):
        self.queue = []

    def push(self, item):
        self.queue.append(item)
        self.queue.sort(key=lambda x: x.priority_level if hasattr(x, 'priority_level') else 99)

    def pop(self):
        if self.queue:
            return self.queue.pop(0)
        return None

    def peek(self):
        if self.queue:
            return self.queue[0]
        return None

    def is_empty(self):
        return len(self.queue) == 0

    def size(self):
        return len(self.queue)

    def get_all(self):
        return self.queue

    def remove(self, item_id):
        self.queue = [item for item in self.queue if item.id != item_id]
