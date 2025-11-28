import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt

from config import Config
from models import db, User, Report, Alert

# create app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

# ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

from auth import auth_bp
from admin import admin_bp
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if current_user.role != "farmer":
        flash("Only farmers can submit reports", "warning")
        return redirect(url_for("index"))

    if request.method == "POST":
        pest = request.form.get("pest") or "Unknown"
        desc = request.form.get("desc") or ""
        lat = request.form.get("lat")
        lon = request.form.get("lon")
        if not lat or not lon:
            flash("Please provide location (use 'Use My Location' if on mobile/desktop).", "danger")
            return redirect(url_for("report"))
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except ValueError:
            flash("Invalid coordinates", "danger")
            return redirect(url_for("report"))

        image_file = request.files.get("image")
        filename = None
        if image_file and image_file.filename:
            filename = secure_filename(f"{datetime.utcnow().timestamp()}_{image_file.filename}")
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image_file.save(save_path)

        new_report = Report(
            user_id=current_user.id,
            pest_name=pest,
            description=desc,
            latitude=lat_f,
            longitude=lon_f,
            image=filename
        )
        db.session.add(new_report)
        db.session.commit()

        # Trigger simple alert check
        check_and_create_alert(lat_f, lon_f, pest)

        flash("Report submitted — thank you!", "success")
        return redirect(url_for("index"))

    return render_template("report.html")


@app.route("/map")
@login_required
def map_view():
    # return JSON of reports for client map
    return render_template("map.html")


@app.route("/api/reports")
def api_reports():
    # Return recent reports as JSON (for map)
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


# --------- Alert logic ----------
def haversine_km(lat1, lon1, lat2, lon2):
    # convert degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    R = 6371  # Earth radius km
    return R * c

def check_and_create_alert(lat, lon, pest_name):
    """
    Check reports within ALERT_WINDOW_DAYS and ALERT_RADIUS_KM; if count >= threshold => create alert.
    This is a simple approach — we cluster by geographic radius.
    """
    window = datetime.utcnow() - timedelta(days=app.config.get("ALERT_WINDOW_DAYS", 7))
    radius_km = app.config.get("ALERT_RADIUS_KM", 5.0)
    threshold = app.config.get("ALERT_THRESHOLD", 3)

    nearby_reports = []
    all_recent = Report.query.filter(Report.created_at >= window).all()
    for r in all_recent:
        distance = haversine_km(lat, lon, r.latitude, r.longitude)
        if distance <= radius_km:
            nearby_reports.append(r)

    if len(nearby_reports) >= threshold:
        # create alert centered at the average of nearby points
        avg_lat = sum([r.latitude for r in nearby_reports]) / len(nearby_reports)
        avg_lon = sum([r.longitude for r in nearby_reports]) / len(nearby_reports)
        msg = f"High pest activity ({len(nearby_reports)} reports) for '{pest_name}' within {radius_km} km."
        alert = Alert(lat=avg_lat, lon=avg_lon, message=msg, severity="high")
        db.session.add(alert)
        db.session.commit()


# create db tables if run directly
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
