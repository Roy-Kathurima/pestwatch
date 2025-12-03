from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(200))
    email = db.Column(db.String(200), unique=True, nullable=True)
    phone = db.Column(db.String(30), nullable=True)                # new: phone for SMS
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship("Report", back_populates="user", cascade="all, delete-orphan")
    login_logs = db.relationship("LoginLog", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, p):
        self.password_hash = generate_password_hash(p)

    def check_password(self, p):
        return check_password_hash(self.password_hash, p)

class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    details = db.Column(db.Text)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    approved = db.Column(db.Boolean, default=False)
    image_filename = db.Column(db.String(300), nullable=True)      # new: stored filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", back_populates="reports")

class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username = db.Column(db.String(120))
    success = db.Column(db.Boolean)
    time = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="login_logs")
