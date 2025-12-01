import os, time
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from models import db, User, Report
from config import Config

auth = Blueprint("auth", __name__)

def save_image(file):
    if not file or file.filename == "":
        return None
    filename = secure_filename(file.filename)
    new_name = f"{int(time.time())}_{filename}"
    file.save(os.path.join(Config.UPLOAD_FOLDER, new_name))
    return new_name

@auth.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(name=request.form["name"],
                    email=request.form["email"],
                    password=generate_password_hash(request.form["password"]))
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/admin/dashboard" if user.is_admin else "/dashboard")
        flash("Invalid credentials")
    return render_template("login.html")

@auth.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.filter_by(user_id=current_user.id)
    return render_template("dashboard.html", reports=reports)

@auth.route("/submit", methods=["POST"])
@login_required
def submit():
    img = save_image(request.files.get("image"))

    report = Report(
        pest_name=request.form["pest"],
        description=request.form["description"],
        location=request.form["location"],
        latitude=request.form.get("latitude"),
        longitude=request.form.get("longitude"),
        image=img,
        user_id=current_user.id
    )
    db.session.add(report)
    db.session.commit()
    return redirect("/dashboard")

@auth.route("/logout")
def logout():
    logout_user()
    return redirect("/login")
