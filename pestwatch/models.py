from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))
    security_question = db.Column(db.String(200))
    security_answer = db.Column(db.String(200))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pest = db.Column(db.String(100))
    location = db.Column(db.String(200))
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    description = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

class LoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
