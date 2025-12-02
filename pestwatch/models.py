from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self,p):
        self.password = generate_password_hash(p)

    def check_password(self,p):
        return check_password_hash(self.password,p)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    details = db.Column(db.Text)
    image = db.Column(db.String(200))
    lat = db.Column(db.String(50))
    lng = db.Column(db.String(50))
    approved = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")

class LoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    ip = db.Column(db.String(100))
    agent = db.Column(db.String(300))
    time = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean)
