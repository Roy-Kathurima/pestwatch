import os
import csv
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, abort, make_response
)
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Report, LoginLog
from config import Config

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize database
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def log_login_attempt(username: str, user_obj, success: bool):
    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")
    log = LoginLog(
        user_id=(user_obj.id if user_obj else None),
        username=username,
        ip_address=ip,
        user_agent=ua,
        timestamp=datetime.utcnow(),
        success=success
    )
    db.session.add(log)
    db.session.commit()

# ---------- Routes ----------

@app.route("/")
def index():
    # show only approved reports on public map
    reports = Report.query.filter_by(approved=True).order_by(Report.created_at.desc()).all()
    return render_template("index.html", reports=reports)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()

        if not username or not password:
            flash("Username and password required", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        user = User(username=username, full_name=full_name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            log_login_attempt(username, user, True)
            # Redirect based on role
            if user.is_admin:
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))
        else:
            log_login_attempt(username, user, False)
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    # farmer dashboard: showing their own reports
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", reports=reports)

@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        details = request.form.get("details", "").strip()
        lat = request.form.get("lat") or None
        lng = request.form.get("lng") or None

        try:
            lat = float(lat) if lat else None
        except ValueError:
            lat = None
        try:
            lng = float(lng) if lng else None
        except ValueError:
            lng = None

        image_file = request.files.get("image")
        filename = None
        if image_file and image_file.filename:
            if not allowed_file(image_file.filename):
                flash("File type not allowed", "danger")
                return redirect(request.url)
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{image_file.filename}")
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(image_path)

        rep = Report(
            title=title,
            details=details,
            image_filename=filename,
            lat=lat,
            lng=lng,
            user=current_user
        )
        db.session.add(rep)
        db.session.commit()
        flash("Report submitted for approval.", "success")
        return redirect(url_for("dashboard"))

    return render_template("farmer_report.html")

@app.route("/my-reports")
@login_required
def my_reports():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("farmer_reports.html", reports=reports)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# --------- Admin routes ----------
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/admin/logins")
@login_required
@admin_required
def admin_logins():
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).all()
    return render_template("admin_logins.html", logs=logs)

@app.route("/admin/approve/<int:report_id>", methods=["POST","GET"])
@login_required
@admin_required
def admin_approve(report_id):
    report = Report.query.get_or_404(report_id)
    report.approved = True
    db.session.commit()
    flash("Report approved.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/export")
@login_required
@admin_required
def admin_export():
    # Export reports to CSV (server-side file, then send to user)
    reports = Report.query.order_by(Report.created_at.desc()).all()
    fieldnames = ["id","title","details","image_filename","lat","lng","approved","created_at","user_id","username"]
    fname = "reports_export.csv"
    with open(fname, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in reports:
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

# route to create an admin user without terminal (use carefully)
@app.route("/make_admin")
def make_admin():
    username = request.args.get("user")
    if not username:
        return "Provide ?user=USERNAME in URL"
    u = User.query.filter_by(username=username).first()
    if not u:
        return "User not found"
    u.is_admin = True
    db.session.commit()
    return f"{username} is now an admin"

# Error handlers
@app.errorhandler(403)
def forbidden(e):
    return render_template("404.html", message="Forbidden (403)"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", message="Not Found (404)"), 404

# Ensure database tables exist on startup (works with Flask 3+)
with app.app_context():
    db.create_all()

# Run with gunicorn in production; if run directly use Flask dev server
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
