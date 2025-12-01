import os
import time
from flask import send_from_directory
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, abort
from config import Config
from models import db, User, Report, Alert
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
from PIL import Image

# create app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

# ensure upload dir
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ----- Helper functions -----
def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    R = 6371
    return R * c

def check_and_create_alert(lat, lon, pest_name):
    window = datetime.utcnow() - timedelta(days=app.config.get("ALERT_WINDOW_DAYS", 7))
    radius_km = app.config.get("ALERT_RADIUS_KM", 5.0)
    threshold = app.config.get("ALERT_THRESHOLD", 3)
    recent = Report.query.filter(Report.created_at >= window).all()
    nearby = [r for r in recent if haversine_km(lat, lon, r.latitude, r.longitude) <= radius_km]
    if len(nearby) >= threshold:
        avg_lat = sum([r.latitude for r in nearby]) / len(nearby)
        avg_lon = sum([r.longitude for r in nearby]) / len(nearby)
        msg = f"High pest activity ({len(nearby)} reports) for '{pest_name}' within {radius_km} km."
        # avoid duplicate identical alert within window
        existing = Alert.query.filter(Alert.created_at >= window).all()
        for e in existing:
            if abs(e.lat - avg_lat) < 0.001 and abs(e.lon - avg_lon) < 0.001 and pest_name in e.message:
                return
        a = Alert(lat=avg_lat, lon=avg_lon, message=msg, severity="high")
        db.session.add(a)
        db.session.commit()

def save_image(file_storage):
    if not file_storage:
        return None
    filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file_storage.filename}")
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file_storage.save(path)
    # optionally validate or resize
    try:
        img = Image.open(path)
        img.verify()
    except Exception:
        os.remove(path)
        return None
    return filename

# ----- Login loader -----
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----- Auto create tables and admin (runs at startup) -----
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@pestwatch.com", is_admin=True)
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("✅ Auto-created admin: admin / admin123")

# ----- Routes -----
@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    return render_template("index.html")

# ----- AUTH ROUTES -----
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not username or not email or not password:
            flash("Username, email and password are required.", "danger")
            return redirect(url_for("register"))
        if User.query.filter((User.username==username)|(User.email==email)).first():
            flash("Username or email already exists.", "warning")
            return redirect(url_for("register"))
        u = User(username=username, email=email, is_admin=False)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash("Registration successful — please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))
        if not user.is_active:
            flash("Account disabled. Contact admin.", "danger")
            return redirect(url_for("login"))
        login_user(user)
        flash("Logged in", "success")
        if user.is_admin:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("index"))

# ----- Farmer Dashboard -----
@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))
    reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", reports=reports)

@app.route("/report/new", methods=["GET","POST"])
@login_required
def new_report():
    if current_user.is_admin:
        flash("Admins cannot submit reports.", "warning")
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        pest = request.form.get("pest","").strip() or "Unknown"
        desc = request.form.get("desc","").strip()
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        if not lat or not lon:
            flash("Location required (use 'Use My Location').", "danger")
            return redirect(url_for("new_report"))
        try:
            latf = float(lat); lonf = float(lon)
        except ValueError:
            flash("Invalid coordinates.", "danger")
            return redirect(url_for("new_report"))
        image_file = request.files.get("image")
        imgname = save_image(image_file) if image_file and image_file.filename else None
        r = Report(user_id=current_user.id, pest_name=pest, description=desc,
                   latitude=latf, longitude=lonf, image=imgname)
        db.session.add(r)
        db.session.commit()
        check_and_create_alert(latf, lonf, pest)
        flash("Report submitted.", "success")
        return redirect(url_for("dashboard"))
    return render_template("report_form.html")

@app.route("/report/<int:rid>/edit", methods=["GET","POST"])
@login_required
def edit_report(rid):
    r = Report.query.get_or_404(rid)
    if r.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    if request.method == "POST":
        r.pest_name = request.form.get("pest","").strip() or r.pest_name
        r.description = request.form.get("desc","").strip()
        lat = request.form.get("lat"); lon = request.form.get("lon")
        if lat and lon:
            try:
                r.latitude = float(lat); r.longitude = float(lon)
            except ValueError:
                flash("Invalid coordinates.", "danger")
                return redirect(url_for("edit_report", rid=rid))
        image_file = request.files.get("image")
        if image_file and image_file.filename:
            img = save_image(image_file)
            if img:
                # remove old image if exists
                if r.image:
                    try: os.remove(os.path.join(app.config["UPLOAD_FOLDER"], r.image))
                    except: pass
                r.image = img
        db.session.commit()
        flash("Report updated.", "success")
        return redirect(url_for("dashboard") if not current_user.is_admin else url_for("admin_view_report", rid=rid))
    return render_template("report_edit.html", r=r)

@app.route("/report/<int:rid>/delete", methods=["POST"])
@login_required
def delete_report(rid):
    r = Report.query.get_or_404(rid)
    if r.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    # delete image
    if r.image:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], r.image))
        except:
            pass
    db.session.delete(r)
    db.session.commit()
    flash("Report deleted.", "info")
    return redirect(url_for("dashboard") if not current_user.is_admin else url_for("admin_dashboard"))

# ----- Admin Dashboard -----
@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    reports = Report.query.order_by(Report.created_at.desc()).limit(200).all()
    return render_template("admin_dashboard.html", reports=reports)

@app.route("/admin/users")
@login_required
def admin_users():
    if not current_user.is_admin:
        abort(403)
    farmers = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=farmers)

@app.route("/admin/user/<int:uid>/toggle", methods=["POST"])
@login_required
def admin_toggle_user(uid):
    if not current_user.is_admin:
        abort(403)
    u = User.query.get_or_404(uid)
    u.is_active = not u.is_active
    db.session.commit()
    flash("User status updated.", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/user/<int:uid>/delete", methods=["POST"])
@login_required
def admin_delete_user(uid):
    if not current_user.is_admin:
        abort(403)
    u = User.query.get_or_404(uid)
    if u.is_admin:
        flash("Cannot delete admin.", "danger")
        return redirect(url_for("admin_users"))
    db.session.delete(u)
    db.session.commit()
    flash("User deleted.", "info")
    return redirect(url_for("admin_users"))

@app.route("/admin/alerts")
@login_required
def admin_alerts():
    if not current_user.is_admin:
        abort(403)
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template("admin_alerts.html", alerts=alerts)

@app.route("/admin/report/<int:rid>")
@login_required
def admin_view_report(rid):
    if not current_user.is_admin:
        abort(403)
    r = Report.query.get_or_404(rid)
    return render_template("admin_view_report.html", r=r)

# ----- Map & API -----
@app.route("/map")
@login_required
def map_view():
    return render_template("map.html")

@app.route("/api/reports")
def api_reports():
    reports = Report.query.order_by(Report.created_at.desc()).limit(1000).all()
    out = []
    for r in reports:
        out.append({
            "id": r.id,
            "pest_name": r.pest_name,
            "description": r.description,
            "lat": r.latitude,
            "lon": r.longitude,
            "image": url_for("uploaded_file", filename=r.image) if r.image else None,
            "created_at": r.created_at.isoformat(),
            "user": r.user.username
        })
    return jsonify(out)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ----- Error handlers -----
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@app.errorhandler(404)
def notfound(e):
    return render_template("404.html"), 404
    @app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # serve from the uploads folder we've created
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# run
if __name__ == "__main__":
    app.run(debug=True)



