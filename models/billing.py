from datetime import datetime
from . import db

class Billing(db.Model):
    __tablename__ = 'billings'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    bill_number = db.Column(db.String(20), unique=True, nullable=False)
    consultation_fee = db.Column(db.Float, default=0.0)
    lab_charges = db.Column(db.Float, default=0.0)
    medication_charges = db.Column(db.Float, default=0.0)
    procedure_charges = db.Column(db.Float, default=0.0)
    room_charges = db.Column(db.Float, default=0.0)
    other_charges = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    balance_due = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='unpaid')
    payment_method = db.Column(db.String(50))
    payment_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    PAYMENT_STATUS = ['unpaid', 'partial', 'paid', 'refunded', 'cancelled']
    PAYMENT_METHODS = ['cash', 'card', 'insurance', 'bank_transfer', 'mobile_money']

    items = db.relationship('BillingItem', backref='bill', lazy=True, cascade='all, delete-orphan')

    def calculate_totals(self):
        self.consultation_fee = self.consultation_fee or 0.0
        self.lab_charges = self.lab_charges or 0.0
        self.medication_charges = self.medication_charges or 0.0
        self.procedure_charges = self.procedure_charges or 0.0
        self.room_charges = self.room_charges or 0.0
        self.other_charges = self.other_charges or 0.0
        self.discount = self.discount or 0.0
        self.tax = self.tax or 0.0
        self.paid_amount = self.paid_amount or 0.0
        self.subtotal = (self.consultation_fee + self.lab_charges + self.medication_charges +
                        self.procedure_charges + self.room_charges + self.other_charges)
        self.total_amount = self.subtotal + self.tax - self.discount
        self.balance_due = self.total_amount - self.paid_amount
        if self.balance_due <= 0 and self.total_amount > 0:
            self.payment_status = 'paid'
        elif self.paid_amount > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'unpaid'

    def to_dict(self):
        return {
            'id': self.id,
            'bill_number': self.bill_number,
            'patient_name': self.patient.full_name if self.patient else 'N/A',
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'balance_due': self.balance_due,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Billing {self.bill_number} - {self.payment_status}>'

class BillingItem(db.Model):
    __tablename__ = 'billing_items'
    id = db.Column(db.Integer, primary_key=True)
    billing_id = db.Column(db.Integer, db.ForeignKey('billings.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    item_type = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<BillingItem {self.item_name}>'
