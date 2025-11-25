# reset_db.py
from app import app
from models import db

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating new tables...")
    db.create_all()
    print("DONE! Database has been reset.")
