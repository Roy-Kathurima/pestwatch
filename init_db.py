from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    # create default admin user (optional; admin logins use ADMIN_PASSWORD not user role)
    print("DB recreated")
