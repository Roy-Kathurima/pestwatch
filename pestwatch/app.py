import os
import csv
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, abort, jsonify
)
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Report, LoginLog
from config import Config
import logging
import os as _os

# Optional Twilio SMS integration (set TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM in Render env)
USE_TWILIO = bool(_os.environ.get("TWILIO_SID") and _os.environ.get("TWILIO_TOKEN") and _os.environ.get("TWILIO_FROM"))
if USE_TWILIO:
    from twilio.rest import Client
    twilio_client = Client(_os.environ.get("TWILIO_SID"), _os.environ.get("TWILIO_TOKEN"))

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app = Flask(__name__)
app.config.from_object(Config)

# Ensure uploads dir exists
os.makedirs(app.config.get("UPLOAD_FOLDER", "./uploads"), exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(uid):
    try:
        return User.query.get(int(uid))
    except Exception:
        return None

def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def log_login(username, success):
    l = LoginLog(username=username, success=success)
    db.session.add(l)
    db.session.commit()

def send_sms(to_number: str, message: str):
    """Send SMS via Twilio if configured; otherwise log."""
    if not to_number:
        logger.info("No phone number to send SMS to.")
        return False
    if USE_TWILIO:
        try:
            twilio_client.messages.create(
                body=message,
                from_=_os.environ.get("TWILIO_FROM"),
                to=to_number
            )
            logger.info(f"Sent SMS to {to_number}")
            return True
        except Exception as e:
            logger.exception("Twilio send failed:")
            return False
    else:
        # fallback: log to server logs
        logger.info(f"[SMS STUB] To: {to_number} Message: {message}")
        return False

# Create DB tables on startup (Flask 3+ friendly)
with app.app_context():
    db.create_all()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    reports = Report.query.filter_by(approved=True) \
        .order_by(Report.created.desc()).all()

    return render_template("index.html", reports=reports)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            security_question=request.form["question"]
        )
        user.set_password(request.form["password"])
        user.set_answer(request.form["answer"])

        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        u = User.query.filter_by(username=username).first()
        ok = False
        if u and u.check_password(password):
            login_user(u)
            ok = True
            flash("Logged in", "success")
            if u.is_admin:
                return redirect(url_for("admin"))
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
        log_login(username, ok)
    return render_template("login.html")

@app.route("/reset-password", methods=["GET","POST"])
def reset_password():
    if request.method == "POST":
        username = request.form["username"]
        user = User.query.filter_by(username=username).first()

        if not user:
            flash("User not found")
            return redirect("/reset-password")

        if user.security_question != request.form["question"]:
            flash("Wrong question selected")
            return redirect("/reset-password")

        if not user.check_answer(request.form["answer"]):
            flash("Wrong answer")
            return redirect("/reset-password")

        if request.form["password"] != request.form["confirm"]:
            flash("Passwords do not match")
            return redirect("/reset-password")

        user.set_password(request.form["password"])
        db.session.commit()

        flash("Password reset success. Login now.")
        return redirect("/login")

    return render_template("reset_password.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

# ---------- USER DASHBOARD ----------
@app.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", reports=reports)

# ---------- PROFILE ----------
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

# ---------- REPORT (with image upload) ----------
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
        except ValueError:
            lat = None
        try:
            lng = float(lng) if lng else None
        except ValueError:
            lng = None

        image = request.files.get("image")
        filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("File type not allowed", "danger")
                return redirect(request.url)
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{image.filename}")
            image.save(os.path.join(app.config.get("UPLOAD_FOLDER","uploads"), filename))

        r = Report(
            title=title,
            details=details,
            lat=lat,
            lng=lng,
            image_filename=filename,
            user_id=current_user.id
        )
        db.session.add(r)
        db.session.commit()
        flash("Report submitted for review", "success")
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

# ---------- ADMIN ----------
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
def admin():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/admin/approve/<int:report_id>", methods=["POST","GET"])
@login_required
@admin_required
def approve(report_id):
    r = Report.query.get_or_404(report_id)
    r.approved = True
    db.session.commit()

    # send SMS to report owner if phone exists
    if r.user and getattr(r.user, "phone", None):
        msg = f"Hello {r.user.username}, your report '{r.title}' has been approved by PestWatch."
        send_sms(r.user.phone, msg)

    flash("Report approved and notification sent (if phone available).", "success")
    return redirect(url_for("admin"))

@app.route("/admin/logins")
@login_required
@admin_required
def admin_logins():
    logs = LoginLog.query.order_by(LoginLog.time.desc()).all()
    return render_template("admin_logins.html", logs=logs)

@app.route("/admin/export")
@login_required
@admin_required
def admin_export():
    fname = "reports_export.csv"
    fieldnames = ["id","title","details","image_filename","lat","lng","approved","created_at","user_id","username"]
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in Report.query.order_by(Report.created_at.desc()).all():
            w.writerow({
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

# API endpoint to drive charts (JSON)
@app.route("/admin/stats")
@login_required
@admin_required
def admin_stats():
    # total approved vs pending
    total_approved = Report.query.filter_by(approved=True).count()
    total_pending = Report.query.filter_by(approved=False).count()

    # reports by day (last 14 days)
    today = datetime.utcnow().date()
    days = []
    counts = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        num = Report.query.filter(
            db.func.date(Report.created_at) == d
        ).count()
        days.append(d.isoformat())
        counts.append(num)

    return jsonify({
        "approved": total_approved,
        "pending": total_pending,
        "days": days,
        "counts": counts
    })

# optional helper to make a user admin (use carefully)
@app.route("/make_admin")
def make_admin():
    username = request.args.get("user")
    if not username:
        return "Provide ?user=USERNAME"
    u = User.query.filter_by(username=username).first()
    if not u:
        return "User not found"
    u.is_admin = True
    db.session.commit()
    return f"{username} is now admin"

# error pages
@app.errorhandler(403)
def forbidden(e):
    return render_template("404.html", message="Forbidden (403)"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", message="Not Found (404)"), 404

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)




