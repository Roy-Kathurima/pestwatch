from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pest_name = db.Column(db.String(120))
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    image = db.Column(db.String(255))
    latitude = db.Column(db.String(80))
    longitude = db.Column(db.String(80))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
