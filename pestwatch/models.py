from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import db, login_manager

# --------------------
# USER MODEL
# --------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    reports = db.relationship("Report", backref="user", lazy=True)

    def set_password(self, pwd):
        self.password = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password, pwd)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --------------------
# REPORT MODEL
# --------------------
class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    details = db.Column(db.Text)
    image = db.Column(db.String(255))
    location = db.Column(db.String(255))
    approved = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


# --------------------
# LOGIN LOG MODEL
# --------------------
class LoginLog(db.Model):
    __tablename__ = "logins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120))
    time = db.Column(db.DateTime, default=datetime.utcnow)
