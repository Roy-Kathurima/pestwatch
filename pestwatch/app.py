import os, csv, io
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    send_from_directory, send_file, jsonify, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Report, LoginLog
from config import Config

# ---- App init ----
app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize DB
db.init_app(app)
with app.app_context():
    db.create_all()

# ---- Helpers ----
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}
def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.context_processor
def inject_user():
    user = None
    if session.get("user_id"):
        user = User.query.get(session["user_id"])
    return {"current_user": user}

def log_login(username, success=True):
    log = LoginLog(
        username=username,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        success=success
    )
    db.session.add(log)
    db.session.commit()

# ---- Routes ----

@app.route("/")
def root():
    # landing -> login page (user requested)
    return redirect(url_for("login"))

# ----- Auth -----
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        question = request.form.get("question","")
        answer = request.form.get("answer","")

        if not username or not password or not answer:
            flash("Please fill username, password and security answer", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username exists", "danger")
            return redirect(url_for("register"))

        u = User(username=username)
        u.set_password(password)
        u.security_question = question
        u.set_security_answer(answer)
        db.session.add(u)
        db.session.commit()
        flash("Account created — please login", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session.permanent = True
            log_login(username, True)
            flash("Welcome back", "success")
            return redirect(url_for("dashboard"))
        else:
            log_login(username, False)
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("admin_unlocked", None)
    flash("Logged out", "info")
    return redirect(url_for("login"))

# ----- Reset password -----
@app.route("/reset_password", methods=["GET","POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        question = request.form.get("question","")
        answer = request.form.get("answer","")
        new_pass = request.form.get("password","")
        confirm = request.form.get("confirm","")

        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User not found", "danger"); return redirect(url_for("reset_password"))
        if user.security_question != question:
            flash("Security question mismatch", "danger"); return redirect(url_for("reset_password"))
        if not user.check_security_answer(answer):
            flash("Security answer incorrect", "danger"); return redirect(url_for("reset_password"))
        if new_pass != confirm:
            flash("Passwords do not match", "danger"); return redirect(url_for("reset_password"))

        user.set_password(new_pass)
        db.session.commit()
        flash("Password reset — please login", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html")

# ----- Dashboard & reports -----
@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    uid = session["user_id"]
    reports = Report.query.filter_by(user_id=uid).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", reports=reports)

@app.route("/report", methods=["GET","POST"])
def report():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form.get("title","").strip()
        details = request.form.get("details","").strip()
        lat = request.form.get("lat") or None
        lng = request.form.get("lng") or None
        try:
            lat = float(lat) if lat else None
            lng = float(lng) if lng else None
        except ValueError:
            lat = None; lng = None

        file = request.files.get("image")
        filename = None
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Invalid image type", "danger"); return redirect(request.url)
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        r = Report(
            title=title,
            details=details,
            image_filename=filename,
            lat=lat,
            lng=lng,
            user_id=session["user_id"]
        )
        db.session.add(r)
        db.session.commit()
        flash("Report submitted for approval", "success")
        return redirect(url_for("dashboard"))
    return render_template("farmer_report.html")

@app.route("/my_reports")
def my_reports():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    reports = Report.query.filter_by(user_id=session["user_id"]).order_by(Report.created_at.desc()).all()
    return render_template("farmer_reports.html", reports=reports)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ----- Admin unlock (visible from home/login) -----
@app.route("/admin_unlock", methods=["GET","POST"])
def admin_unlock():
    secret_env = os.environ.get("ADMIN_SECRET", "letmein")
    if request.method == "POST":
        code = request.form.get("code","")
        if code == secret_env:
            session["admin_unlocked"] = True
            flash("Admin unlocked for this session", "success")
            return redirect(url_for("admin"))
        flash("Wrong secret", "danger"); return redirect(url_for("admin_unlock"))
    return render_template("admin_unlock.html")

def admin_guard():
    """Return True if request allowed for admin pages"""
    # logged-in admin user OR session-unlocked via secret
    if session.get("admin_unlocked"):
        return True
    if session.get("user_id"):
        u = User.query.get(session["user_id"])
        if u and u.is_admin:
            return True
    return False

# ----- Admin pages -----
@app.route("/admin")
def admin():
    if not admin_guard():
        return redirect(url_for("admin_unlock"))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/admin/approve/<int:report_id>", methods=["POST"])
def admin_approve(report_id):
    if not admin_guard():
        return redirect(url_for("admin_unlock"))
    r = Report.query.get_or_404(report_id)
    r.approved = True
    db.session.commit()
    flash("Report approved", "success")
    return redirect(url_for("admin"))

@app.route("/admin/logins")
def admin_logins():
    if not admin_guard():
        return redirect(url_for("admin_unlock"))
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).all()
    return render_template("admin_logins.html", logs=logs)

@app.route("/admin/export")
def admin_export():
    if not admin_guard():
        return redirect(url_for("admin_unlock"))
    fname = "reports_export.csv"
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(["id","title","details","image_filename","lat","lng","approved","created_at","user_id"])
    for r in Report.query.order_by(Report.created_at.desc()).all():
        writer.writerow([r.id, r.title or "", r.details or "", r.image_filename or "", r.lat or "", r.lng or "", r.approved, r.created_at.isoformat(), r.user_id])
    output = io.BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=fname, mimetype="text/csv")

# ----- admin stats for charts -----
@app.route("/admin/stats")
def admin_stats():
    if not admin_guard():
        abort(403)
    total_approved = Report.query.filter_by(approved=True).count()
    total_pending = Report.query.filter_by(approved=False).count()
    # last 14 days
    today = datetime.utcnow().date()
    days = []
    counts = []
    for i in range(13,-1,-1):
        d = today - timedelta(days=i)
        c = Report.query.filter(db.func.date(Report.created_at)==d).count()
        days.append(d.isoformat()); counts.append(c)
    return jsonify({"approved": total_approved, "pending": total_pending, "days": days, "counts": counts})

# ----- simple profile -----
@app.route("/profile", methods=["GET","POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        user.full_name = request.form.get("full_name","").strip()
        user.email = request.form.get("email","").strip()
        user.phone = request.form.get("phone","").strip()
        db.session.commit()
        flash("Profile updated", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)

# ----- errors -----
@app.errorhandler(403)
def forbidden(e):
    return render_template("404.html", message="Forbidden (403)"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", message="Not found (404)"), 404

# ----- run -----
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
