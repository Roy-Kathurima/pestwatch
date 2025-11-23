# app.py
import os
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, asin
from models import db, User, Report
from config import Config

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists in both local and deployed envs
    upload_folder = app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        # Fallback to default inside project
        upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
        app.config["UPLOAD_FOLDER"] = upload_folder
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    # create tables on first request if they don't exist (safe for small apps)
    @app.before_first_request
    def ensure_tables():
        with app.app_context():
            db.create_all()

    # simple error handler for 500, 404
    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Server Error: {e}, path: {request.path}")
        return render_template("500.html"), 500

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app

app = create_app()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def check_for_alerts(lat, lon, radius_km=5, hours=24, threshold=5):
    since = datetime.utcnow() - timedelta(hours=hours)
    reports = Report.query.filter(Report.created_at >= since).all()
    count = 0
    for r in reports:
        try:
            if haversine(lat, lon, r.latitude, r.longitude) <= radius_km:
                count += 1
        except Exception:
            continue
    return count >= threshold, count

# ---------------- Routes ----------------

@app.route("/")
def index():
    return render_template("welcome.html")

# ---------------- Authentication (Farmers) ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not fullname or not email or not password:
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for("register"))

        user = User(fullname=fullname, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Login now.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.fullname
            flash("Login successful.")
            return redirect(url_for("dashboard"))
        flash("Invalid credentials.")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    reports = user.reports if user else []
    return render_template("dashboard.html", user=user, reports=reports)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for("index"))

# ---------------- Report Submission ----------------

@app.route("/report", methods=["GET", "POST"])
def report():
    if not session.get("user_id"):
        flash("Please login to submit a report.")
        return redirect(url_for("login"))

    if request.method == "POST":
        description = request.form.get("description", "").strip()
        severity = request.form.get("severity", "Low")
        lat = request.form.get("latitude")
        lon = request.form.get("longitude")

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            flash("Please provide a valid location (use the map).")
            return redirect(url_for("report"))

        file = request.files.get("image")
        filename = None
        if file and allowed_file(file.filename):
            safe = secure_filename(file.filename)
            filename = f"{int(datetime.utcnow().timestamp())}_{safe}"
            dest = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(dest)

        r = Report(
            farmer_id=session["user_id"],
            description=description,
            image_filename=filename,
            latitude=lat,
            longitude=lon,
            severity=severity
        )
        db.session.add(r)
        db.session.commit()

        alert, count = check_for_alerts(lat, lon)
        if alert:
            flash(f"ALERT: {count} recent reports near this location.")
        else:
            flash("Report submitted. Thank you.")

        return redirect(url_for("thanks"))

    return render_template("report.html")

@app.route("/thanks")
def thanks():
    return render_template("thanks.html")

# ---------------- Admin ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == app.config.get("ADMIN_PASSWORD"):
            session["admin"] = True
            flash("Admin login successful.")
            return redirect(url_for("admin_dashboard"))
        flash("Wrong admin password.")
        return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    # counts for overview
    total = Report.query.count()
    verified_count = Report.query.filter_by(verified=True).count()
    return render_template("admin_dashboard.html", reports=reports, total=total, verified_count=verified_count)

@app.route("/admin/toggle_verify/<int:report_id>", methods=["POST"])
def admin_toggle_verify(report_id):
    if not session.get("admin"):
        return jsonify({"error": "unauthorized"}), 403
    r = Report.query.get(report_id)
    if not r:
        return jsonify({"error": "not found"}), 404
    r.verified = not r.verified
    db.session.commit()
    return jsonify({"success": True, "verified": r.verified})

@app.route("/admin/feedback/<int:report_id>", methods=["POST"])
def admin_feedback(report_id):
    if not session.get("admin"):
        abort(403)
    r = Report.query.get(report_id)
    if not r:
        abort(404)
    text = request.form.get("feedback", "").strip()
    r.admin_feedback = text
    db.session.commit()
    flash("Feedback saved.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_report/<int:report_id>", methods=["POST"])
def admin_delete_report(report_id):
    if not session.get("admin"):
        abort(403)
    r = Report.query.get(report_id)
    if not r:
        abort(404)
    db.session.delete(r)
    db.session.commit()
    flash("Report deleted.")
    return redirect(url_for("admin_dashboard"))

# ---------------- API & uploads ----------------

@app.route("/api/reports")
def api_reports():
    reps = Report.query.order_by(Report.created_at.desc()).all()
    result = []
    for r in reps:
        result.append({
            "id": r.id,
            "user": r.farmer.fullname if r.farmer else "Unknown",
            "description": r.description,
            "lat": r.latitude,
            "lon": r.longitude,
            "severity": r.severity,
            "verified": r.verified,
            "admin_feedback": r.admin_feedback,
            "created_at": r.created_at.isoformat(),
            "image": url_for("uploaded_file", filename=r.image_filename) if r.image_filename else None
        })
    return jsonify(result)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

# ---------------- Utility ----------------

if __name__ == "__main__":
    # only for local development
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
