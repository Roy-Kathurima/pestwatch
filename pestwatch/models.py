from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="farmer")
    question = db.Column(db.String(200))
    answer = db.Column(db.String(200))

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pest = db.Column(db.String(100))
    location = db.Column(db.String(100))
    lat = db.Column(db.String(50))
    lon = db.Column(db.String(50))
    status = db.Column(db.String(20), default="Pending")

class LoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
