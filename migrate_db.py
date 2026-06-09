"""Run locally to migrate SQLite data to Render PostgreSQL.
Usage: py migrate_db.py
"""
import os
from app import create_app, init_database
from models import db

SQLITE_URL = 'sqlite:///instance/hospital.db'
POSTGRES_URL = input("Paste your Render PostgreSQL Internal Database URL: ").strip()

# Export from SQLite
sq_app = create_app('development')
sq_app.config['SQLALCHEMY_DATABASE_URI'] = SQLITE_URL
with sq_app.app_context():
    db.init_app(sq_app)
    db.create_all()
    from models import User, Doctor, Department, Patient, Appointment, MedicalRecord
    from models import Prescription, Triage, Billing, BillingItem, EmergencyQueue
    from models import Notification, ActivityLog

    models = [Department, User, Doctor, Patient, Appointment, MedicalRecord,
              Prescription, Triage, Billing, BillingItem, EmergencyQueue,
              Notification, ActivityLog]

    all_data = {}
    for m in models:
        rows = m.query.all()
        if rows:
            all_data[m.__tablename__] = [r.to_dict() if hasattr(r, 'to_dict') else {c.name: getattr(r, c.name) for c in m.__table__.columns} for r in rows]
            print(f'  Exported {len(rows)} from {m.__tablename__}')

# Import to PostgreSQL
pg_app = create_app('production')
pg_app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRES_URL
with pg_app.app_context():
    db.init_app(pg_app)
    db.create_all()
    from models import User, Doctor, Department, Patient, Appointment, MedicalRecord
    from models import Prescription, Triage, Billing, BillingItem, EmergencyQueue
    from models import Notification, ActivityLog

    model_map = {m.__tablename__: m for m in [Department, User, Doctor, Patient,
                 Appointment, MedicalRecord, Prescription, Triage, Billing,
                 BillingItem, EmergencyQueue, Notification, ActivityLog]}

    for table_name, rows in all_data.items():
        m = model_map.get(table_name)
        if not m or not rows:
            continue
        for row_data in rows:
            try:
                # Remove keys not in model columns
                cols = {c.name for c in m.__table__.columns}
                clean = {k: v for k, v in row_data.items() if k in cols and v is not None}
                # Handle dates/booleans
                for k, v in clean.items():
                    if hasattr(v, 'isoformat'):
                        clean[k] = v.isoformat() if 'date' in k.lower() else v
                db.session.execute(m.__table__.insert(), clean)
            except Exception as e:
                print(f'  Skipped row in {table_name}: {e}')
        db.session.commit()
        print(f'  Imported {len(rows)} into {table_name}')

    # Reset sequences
    for table_name in model_map:
        try:
            db.session.execute(db.text(f"SELECT setval('{table_name}_id_seq', (SELECT MAX(id) FROM {table_name}))"))
        except:
            pass
    db.session.commit()

print('\nMigration complete! Now set DATABASE_URL on Render and deploy.')
