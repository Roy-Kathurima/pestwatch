# app.py
import os
import csv
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, abort, jsonify, session
)
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Report, LoginLog
from config import Config
import logging

app = Flask(__name__)
app.config.from_object(Config)

# ensure upload folder exists
os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

# initialize DB (models.db is defined in models.py)
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def log_login_attempt(username: str, user_obj, success: bool):
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")
    log = LoginLog(user_id=(user_obj.id if user_obj else None),
                   username=username, ip_address=ip, user_agent=ua,
                   timestamp=datetime.utcnow(), success=success)
    db.session.add(log)
    db.session.commit()

# create tables on startup
with app.app_context():
    db.create_all()

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    # public page — show approved reports on homepage
    reports = Report.query.filter_by(approved=True).order_by(Report.created_at.desc()).all()
    return render_template("index.html", reports=reports)

# ---------- Register ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        question = request.form.get("question","").strip()
        answer = request.form.get("answer","").strip()

        if not username or not password or not answer:
            flash("Username, password and security answer are required.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        u = User(username=username)
        u.set_password(password)
        u.security_question = question
        u.set_security_answer(answer)
        db.session.add(u)
        db.session.commit()
        flash("Account created. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# ---------- Login ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            log_login_attempt(username, user, True)
            flash("Logged in", "success")
            return redirect(url_for("dashboard"))
        else:
            log_login_attempt(username, user, False)
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

# ---------- Logout ----------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

# ---------- Dashboard (shows admin unlock link) ----------
@app.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", reports=reports)

# ---------- Admin unlock (secret) ----------
@app.route("/admin_unlock", methods=["GET","POST"])
@login_required
def admin_unlock():
    """
    Allows a logged-in user to enter the secret code to unlock admin view.
    The secret code is read from env var ADMIN_SECRET (recommended).
    Default fallback is 'letmein' — change it in production.
    """
    if request.method == "POST":
        code = request.form.get("code","")
        secret = os.environ.get("ADMIN_SECRET", "letmein")
        if code == secret:
            session["admin_unlocked"] = True
            flash("Admin unlocked for this session.", "success")
            return redirect(url_for("admin"))
        else:
            flash("Wrong secret code.", "danger")
            return redirect(url_for("admin_unlock"))
    return render_template("admin_unlock.html")

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        # allowed if user.is_admin OR session unlocked
        unlocked = session.get("admin_unlocked", False)
        if not current_user.is_authenticated:
            abort(403)
        if current_user.is_admin or unlocked:
            return f(*args, **kwargs)
        abort(403)
    return wrapper

# ---------- Admin page ----------
@app.route("/admin")
@login_required
@admin_required
def admin():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/admin/approve/<int:report_id>", methods=["POST","GET"])
@login_required
@admin_required
def admin_approve(report_id):
    r = Report.query.get_or_404(report_id)
    r.approved = True
    db.session.commit()
    flash("Report approved.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/logins")
@login_required
@admin_required
def admin_logins():
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).all()
    return render_template("admin_logins.html", logs=logs)

@app.route("/admin/export")
@login_required
@admin_required
def admin_export():
    fname = "reports_export.csv"
    fieldnames = ["id","title","details","image_filename","lat","lng","approved","created_at","user_id","username"]
    with open(fname, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in Report.query.order_by(Report.created_at.desc()).all():
            writer.writerow({
                "id": r.id,
                "title": r.title or "",
                "details": r.details or "",
                "image_filename": r.image_filename or "",
                "lat": r.lat if r.lat is not None else "",
                "lng": r.lng if r.lng is not None else "",
                "approved": r.approved,
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "user_id": r.user_id,
                "username": r.user.username if r.user else ""
            })
    return send_from_directory(".", fname, as_attachment=True)

# ---------- Profile ----------
@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name","").strip()
        current_user.email = request.form.get("email","").strip()
        current_user.phone = request.form.get("phone","").strip()
        db.session.commit()
        flash("Profile updated", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html")

# ---------- Report creation (with image upload) ----------
@app.route("/report", methods=["GET","POST"])
@login_required
def report():
    if request.method == "POST":
        title = request.form.get("title","").strip()
        details = request.form.get("details","").strip()
        lat = request.form.get("lat") or None
        lng = request.form.get("lng") or None
        try:
            lat = float(lat) if lat else None
            lng = float(lng) if lng else None
        except ValueError:
            lat = None
            lng = None

        image_file = request.files.get("image")
        filename = None
        if image_file and image_file.filename:
            if not allowed_file(image_file.filename):
                flash("Invalid image type", "danger")
                return redirect(request.url)
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{image_file.filename}")
            image_file.save(os.path.join(app.config.get("UPLOAD_FOLDER","uploads"), filename))

        rep = Report(
            title=title,
            details=details,
            image_filename=filename,
            lat=lat,
            lng=lng,
            user_id=current_user.id
        )
        db.session.add(rep)
        db.session.commit()
        flash("Report submitted for approval", "success")
        return redirect(url_for("dashboard"))
    return render_template("farmer_report.html")

@app.route("/my-reports")
@login_required
def my_reports():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("farmer_reports.html", reports=reports)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config.get("UPLOAD_FOLDER","uploads"), filename)

# ---------- Reset password (security question verification) ----------
@app.route("/reset-password", methods=["GET","POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        question = request.form.get("question","").strip()
        answer = request.form.get("answer","").strip()
        new_pass = request.form.get("password","")
        confirm = request.form.get("confirm","")

        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User not found", "danger")
            return redirect(url_for("reset_password"))

        if user.security_question != question:
            flash("Security question does not match", "danger")
            return redirect(url_for("reset_password"))

        if not user.check_security_answer(answer):
            flash("Security answer incorrect", "danger")
            return redirect(url_for("reset_password"))

        if new_pass != confirm:
            flash("Passwords do not match", "danger")
            return redirect(url_for("reset_password"))

        user.set_password(new_pass)
        db.session.commit()
        flash("Password reset successful — please login.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")

# ---------- Chart stats endpoint (for admin charts) ----------
@app.route("/admin/stats")
@login_required
@admin_required
def admin_stats():
    total_approved = Report.query.filter_by(approved=True).count()
    total_pending = Report.query.filter_by(approved=False).count()
    today = datetime.utcnow().date()
    days = []
    counts = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        num = Report.query.filter(db.func.date(Report.created_at) == d).count()
        days.append(d.isoformat())
        counts.append(num)
    return jsonify({"approved": total_approved, "pending": total_pending, "days": days, "counts": counts})

# ---------- make_admin helper (optional) ----------
@app.route("/make_admin")
@login_required
def make_admin():
    # WARNING: Only use briefly and remove later if in production
    current_user.is_admin = True
    db.session.commit()
    return "You are now admin"

# ---------- errors ----------
@app.errorhandler(403)
def forbidden(e):
    return render_template("404.html", message="Forbidden (403)"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", message="Not found (404)"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
