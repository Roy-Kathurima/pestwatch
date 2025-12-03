# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(200), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    # security question/answer (for free reset)
    security_question = db.Column(db.String(300), nullable=True)
    security_answer_hash = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reports = db.relationship("Report", back_populates="user", cascade="all, delete-orphan")
    login_logs = db.relationship("LoginLog", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def set_security_answer(self, answer: str):
        self.security_answer_hash = generate_password_hash(answer)

    def check_security_answer(self, answer: str) -> bool:
        if not self.security_answer_hash:
            return False
        return check_password_hash(self.security_answer_hash, answer)


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=True)
    details = db.Column(db.Text, nullable=True)
    image_filename = db.Column(db.String(300), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", back_populates="reports")


class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    username = db.Column(db.String(120), nullable=True)
    ip_address = db.Column(db.String(120), nullable=True)
    user_agent = db.Column(db.String(400), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="login_logs")
