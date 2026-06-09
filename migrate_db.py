"""Migrate SQLite data to Neon PostgreSQL.
Usage: py migrate_db.py
"""
import os, sys
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

SQLITE_PATH = os.path.join(BASE_DIR, 'instance', 'hospital.db')
POSTGRES_URL = sys.argv[1] if len(sys.argv) > 1 else input("Paste your Neon Database URL: ").strip()

# ---- 1. Export from SQLite using raw sqlite3 ----
import sqlite3
conn = sqlite3.connect(SQLITE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row['name'] for row in cursor.fetchall()]
print(f"SQLite tables: {tables}")

all_data = {}
for table in tables:
    cursor.execute(f"SELECT * FROM [{table}]")
    rows = cursor.fetchall()
    if rows:
        all_data[table] = [dict(r) for r in rows]
        print(f"  Exported {len(rows)} from {table}")
conn.close()

# ---- 2. Import into PostgreSQL using the global db with Neon URL ----
os.environ['DATABASE_URL'] = POSTGRES_URL

from app import create_app, init_database
from models import db

app = create_app('production')
init_database(app)

with app.app_context():
    from models import User, Doctor, Department, Patient, Appointment, MedicalRecord
    from models import Prescription, Triage, Billing, BillingItem, EmergencyQueue
    from models import Notification, ActivityLog

    model_map = {m.__tablename__: m for m in [Department, User, Doctor, Patient,
                 Appointment, MedicalRecord, Prescription, Triage, Billing,
                 BillingItem, EmergencyQueue, Notification, ActivityLog]}

    # Clear existing data
    for m in model_map.values():
        try:
            db.session.execute(db.text(f'TRUNCATE TABLE {m.__tablename__} CASCADE'))
        except Exception:
            pass
    db.session.commit()
    print('Cleared existing data in PostgreSQL')

    # Import in FK-safe order
    table_order = ['departments', 'users', 'doctors', 'patients', 'notifications',
                   'billings', 'billing_items', 'appointments', 'medical_records',
                   'prescriptions', 'triages', 'emergency_queue', 'activity_logs']

    for table_name in table_order:
        if table_name not in all_data:
            continue
        rows = all_data[table_name]
        m = model_map.get(table_name)
        if not m or not rows:
            print(f'  Skipped {table_name}: no matching model or empty')
            continue

        col_types = {}
        for c in m.__table__.columns:
            col_types[c.name] = str(c.type.python_type)

        success = 0
        for row_data in rows:
            try:
                clean = {}
                for k, v in row_data.items():
                    if k not in col_types or v is None:
                        continue
                    t = col_types[k]
                    if "datetime.datetime" in t and isinstance(v, str):
                        v = datetime.fromisoformat(v)
                    elif "datetime.date" in t and isinstance(v, str):
                        v = date.fromisoformat(v)
                    clean[k] = v
                db.session.execute(m.__table__.insert(), clean)
                success += 1
            except Exception as e:
                db.session.rollback()
                err_msg = str(e).encode('ascii', 'replace').decode('ascii')
                print(f'  Skipped row in {table_name}: {err_msg[:200]}')
        db.session.commit()
        print(f'  Imported {success} into {table_name}')

    # Reset sequences
    for table_name in model_map:
        try:
            db.session.execute(
                db.text(f"SELECT setval('{table_name}_id_seq', "
                        f"(SELECT COALESCE(MAX(id), 1) FROM {table_name}))")
            )
        except Exception:
            pass
    db.session.commit()

print('\nMigration complete!')
