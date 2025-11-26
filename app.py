from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "pestwatch-secret"

# DATABASE
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # farmer/admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reports = db.relationship("Report", backref="user", lazy=True)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pest = db.Column(db.String(200))
    crop = db.Column(db.String(200))
    description = db.Column(db.Text)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


# ------------- DB CREATE ----------------
with app.app_context():
    db.create_all()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("welcome.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect("/register")

        user = User(username=username, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request
