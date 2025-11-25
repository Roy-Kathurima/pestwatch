# init_db.py
"""
Optional local helper to drop/create database tables and seed admin.
Run locally (not on Render): python init_db.py
This uses the same config in config.py and will create sqlite DB if DATABASE_URL is not set.
"""
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash
import os

app = create_app()
with app.app_context():
    print("Dropping all tables (if any)...")
    db.drop_all()
    print("Creating tables...")
    db.create_all()
    admin_pwd = app.config["ADMIN_PASSWORD"]
    admin_email = app.config.get("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    if not User.query.filter_by(email=admin_email).first():
        admin = User(fullname="Admin", email=admin_email, password_hash=generate_password_hash(admin_pwd), role="admin")
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin {admin_email} with ADMIN_PASSWORD.")
    else:
        print("Admin already exists.")
    print("Done.")
