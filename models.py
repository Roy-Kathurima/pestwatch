from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reports = db.relationship('Report', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    pest_type = db.Column(db.String(100), nullable=True)
    severity = db.Column(db.String(50), nullable=True)
    image_filename = db.Column(db.String(256), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified = db.Column(db.Boolean, default=False)
    admin_feedback = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Report {self.title} by {self.user_id}>"
