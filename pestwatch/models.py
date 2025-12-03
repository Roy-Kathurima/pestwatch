from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    is_admin = db.Column(db.Boolean, default=False)
    security_question = db.Column(db.String(300))
    security_answer_hash = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, hash_text):
        self.password_hash = hash_text

    def check_password(self, password_check):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password_check)

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250))
    details = db.Column(db.Text)
    image_filename = db.Column(db.String(300))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120))
    ip_address = db.Column(db.String(120))
    user_agent = db.Column(db.String(400))
    success = db.Column(db.Boolean, default=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
