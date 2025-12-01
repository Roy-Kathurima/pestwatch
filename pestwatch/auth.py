import os, time
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Report
from datetime import datetime

auth_bp = Blueprint("auth", __name__)

ALLOWED_EXT = {"png","jpg","jpeg","gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXT

def save_image(file_storage):
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    filename = f"{int(time.time())}_{filename}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(dest)
    return filename

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        if not username or not email or not password:
            flash("All fields required", "danger")
            return redirect(url_for("auth.register"))
        if User.query.filter((User.username==username)|(User.email==email)).first():
            flash("User exists", "warning")
            return redirect(url_for("auth.register"))
        u = User(username=username, email=email, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()
        flash("Registered — please login", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        name_or_email = request.form.get("username").strip()
        pwd = request.form.get("password")
        # allow login by username or email
        user = User.query.filter((User.username==name_or_email)|(User.email==name_or_email)).first()
        if not user or not check_password_hash(user.password_hash, pwd):
            flash("Invalid credentials", "danger")
            return redirect(url_for("auth.login"))
        if not user.is_active:
            flash("Account disabled", "danger")
            return redirect(url_for("auth.login"))
        login_user(user)
        flash("Logged in", "success")
        if user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("auth.dashboard"))
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", reports=reports)

@auth_bp.route("/report", methods=["GET","POST"])
@login_required
def report():
    if current_user.is_admin:
        flash("Admins cannot submit reports", "warning")
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        pest = request.form.get("pest") or "Unknown"
        desc = request.form.get("description") or ""
        lat = request.form.get("latitude")
        lon = request.form.get("longitude")
        if not lat or not lon:
            flash("Please provide location (use device location).", "danger")
            return redirect(url_for("auth.report"))
        try:
            latf = float(lat); lonf = float(lon)
        except ValueError:
            flash("Invalid coordinates", "danger")
            return redirect(url_for("auth.report"))
        file = request.files.get("image")
        imgname = save_image(file) if file and file.filename else None
        r = Report(user_id=current_user.id, pest_name=pest, description=desc,
                   latitude=latf, longitude=lonf, image=imgname)
        db.session.add(r)
        db.session.commit()
        flash("Report submitted", "success")
        return redirect(url_for("auth.dashboard"))
    return render_template("report.html")

@auth_bp.route("/report/<int:rid>/edit", methods=["GET","POST"])
@login_required
def report_edit(rid):
    r = Report.query.get_or_404(rid)
    if r.user_id != current_user.id and not current_user.is_admin:
        flash("Not allowed", "danger")
        return redirect(url_for("auth.dashboard"))
    if request.method == "POST":
        r.pest_name = request.form.get("pest", r.pest_name)
        r.description = request.form.get("description", r.description)
        lat = request.form.get("latitude"); lon = request.form.get("longitude")
        if lat and lon:
            try:
                r.latitude = float(lat); r.longitude = float(lon)
            except ValueError:
                flash("Invalid coords", "danger")
                return redirect(url_for("auth.report_edit", rid=rid))
        file = request.files.get("image")
        if file and file.filename:
            img = save_image(file)
            if img:
                # remove previous if exists
                if r.image:
                    try:
                        os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], r.image))
                    except:
                        pass
                r.image = img
        db.session.commit()
        flash("Report updated", "success")
        return redirect(url_for("auth.dashboard"))
    return render_template("report_edit.html", r=r)

@auth_bp.route("/report/<int:rid>/delete", methods=["POST"])
@login_required
def report_delete(rid):
    r = Report.query.get_or_404(rid)
    if r.user_id != current_user.id and not current_user.is_admin:
        flash("Not allowed", "danger")
        return redirect(url_for("auth.dashboard"))
    if r.image:
        try:
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], r.image))
        except:
            pass
    db.session.delete(r)
    db.session.commit()
    flash("Deleted", "info")
    return redirect(url_for("auth.dashboard"))
