from app import create_app
from models import db
from config import Config
import os

app = create_app()

with app.app_context():
    print("Creating database tables (if not exist)...")
    db.create_all()
    print("Done.")
    # optional: create a demo admin user (not necessary—admin uses password)
    # optional: create a demo farmer for testing
    # from models import User
    # if not User.query.filter_by(email="demo@example.com").first():
    #     u = User(fullname="Demo Farmer", email="demo@example.com")
    #     u.set_password("password123")
    #     db.session.add(u)
    #     db.session.commit()
