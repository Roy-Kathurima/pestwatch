import os, io, csv
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    send_file, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Report, LoginLog
from config import Config

# ---- app init ----
app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
with app.app_context():
    db.create_all()

# ---- helpers ----
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.context_processor
def inject_user():
    user = None
    if session.get("user_id"):
        user = User.query.get(session["user_id"])
    return dict(current_user=user)

def log_login(username, success=True):
    log = LoginLog(
        username=username,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        success=success
    )
    db.session.add(log)
    db.session.commit()

def admin_guard():
    # admin if logged-in user is admin OR admin_unlocked in session
    if session.get("admin_unlocked"):
        return True
    if session.get("user_id"):
        u = User.query.get(session["user_id"])
        if u and u.is_admin:
            return True
    return False

# ---- routes ----

@app.route("/")
def index():
    # Landing page shows latest approved reports and login/register links
    reports = Report.query.filter_by(approved=True).order_by(Report.created_at.desc()).limit(100).all()
    # convert to simple dicts for JS map rendering
    reports_json = [
        {
            "id": r.id,
            "title": r.title,
            "details": (r.details[:180] + "...") if r.details and len(r.details) > 180 else (r.details or ""),
            "lat": r.lat, "lng": r.lng,
            "image": r.image_filename,
            "created_at": r.created_at.isoformat()
        } for r in reports
    ]
    return render_template("index.html", reports=reports, reports_json=reports_json)

# ---- auth: register/login/logout ----
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        question = request.form.get("question", "")
        answer = request.form.get("answer", "")

        if not username or not password or not answer:
            flash("Please fill username, password and security answer", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "warning")
            return redirect(url_for("register"))

        u = User(
            username=username,
            password_hash=generate_password_hash(password),
            security_question=question,
            security_answer_hash=generate_password_hash(answer)
        )
        db.session.add(u)
        db.session.commit()
        flash("Account created. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        u = User.query.filter_by(username=username).first()
        if u and check_password_hash(u.password_hash, password):
            session["user_id"] = u.id
            session.permanent = True
            log_login(username, True)
            flash(f"Welcome {u.username}", "success")
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
    return redirect(url_for("index"))

# ---- password reset (security question) ----
@app.route("/reset", methods=["GET","POST"])
def reset():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        question = request.form.get("question","")
        answer = request.form.get("answer","")
        new_password = request.form.get("password","")
        confirm = request.form.get("confirm","")

        u = User.query.filter_by(username=username).first()
        if not u:
            flash("User not found", "danger"); return redirect(url_for("reset"))
        if u.security_question != question:
            flash("Security question mismatch", "danger"); return redirect(url_for("reset"))
        if not check_password_hash(u.security_answer_hash, answer):
            flash("Security answer incorrect", "danger"); return redirect(url_for("reset"))
        if new_password != confirm:
            flash("Passwords do not match", "danger"); return redirect(url_for("reset"))

        u.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("Password reset successful. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html")

# ---- profile ----
@app.route("/profile", methods=["GET","POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    u = User.query.get(session["user_id"])
    if request.method == "POST":
        u.full_name = request.form.get("full_name","").strip()
        u.email = request.form.get("email","").strip()
        u.phone = request.form.get("phone","").strip()
        db.session.commit()
        flash("Profile updated", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=u)

# ---- dashboard & reports ----
@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    # show approved reports to user plus their own submitted reports
    approved = Report.query.filter_by(approved=True).order_by(Report.created_at.desc()).limit(20).all()
    my_reports = Report.query.filter_by(user_id=session["user_id"]).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", approved=approved, my_reports=my_reports)

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
                flash("Invalid image type", "danger")
                return redirect(request.url)
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        r = Report(
            title=title,
            details=details,
            image_filename=filename,
            lat=lat,
            lng=lng,
            user_id=session["user_id"],
            approved=False
        )
        db.session.add(r)
        db.session.commit()
        flash("Report submitted; awaiting approval", "success")
        return redirect(url_for("dashboard"))
    return render_template("farmer_report.html")

@app.route("/my_reports")
def my_reports():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    reports = Report.query.filter_by(user_id=session["user_id"]).order_by(Report.created_at.desc()).all()
    return render_template("farmer_reports.html", reports=reports)

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---- admin unlock & admin area ----
@app.route("/admin_unlock", methods=["GET","POST"])
def admin_unlock():
    if request.method == "POST":
        code = request.form.get("code","")
        if code == app.config.get("ADMIN_UNLOCK_CODE"):
            session["admin_unlocked"] = True
            flash("Admin unlocked for this session", "success")
            return redirect(url_for("admin"))
        else:
            flash("Wrong secret code", "danger")
            return redirect(url_for("admin_unlock"))
    return render_template("admin_unlock.html")

@app.route("/admin")
def admin():
    if not admin_guard():
        return redirect(url_for("admin_unlock"))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/admin/approve/<int:id>", methods=["POST"])
def admin_approve(id):
    if not admin_guard():
        return redirect(url_for("admin_unlock"))
    r = Report.query.get_or_404(id)
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

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["id","title","details","image_filename","lat","lng","approved","created_at","user_id"])
    for r in Report.query.order_by(Report.created_at.desc()).all():
        cw.writerow([r.id, r.title or "", (r.details or "").replace("\n"," "), r.image_filename or "", r.lat or "", r.lng or "", r.approved, r.created_at.isoformat(), r.user_id or ""])
    output = io.BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="reports.csv", mimetype="text/csv")

# ---- admin stats endpoint for charts ----
@app.route("/admin/stats")
def admin_stats():
    if not admin_guard():
        abort(403)
    approved = Report.query.filter_by(approved=True).count()
    pending = Report.query.filter_by(approved=False).count()
    # last 14 days counts
    days = []
    counts = []
    today = datetime.utcnow().date()
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        days.append(d.isoformat())
        c = Report.query.filter(db.func.date(Report.created_at) == d).count()
        counts.append(c)
    return jsonify({"approved": approved, "pending": pending, "days": days, "counts": counts})

# ---- errors ----
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# ---- run ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
