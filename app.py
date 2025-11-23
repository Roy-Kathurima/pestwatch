import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from models import db, User, Report
from config import Config
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, asin

ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'static', 'uploads')), exist_ok=True)

    db.init_app(app)

    # create tables on startup (safe for small apps)
    with app.app_context():
        db.create_all()

    return app

app = create_app()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

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
    count = sum(1 for r in reports if haversine(lat, lon, r.latitude, r.longitude) <= radius_km)
    return count >= threshold, count

# ---------- Routes ----------

@app.route('/', endpoint='index')
def home():
    return render_template('welcome.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        if not (fullname and email and password):
            flash("Complete all fields.")
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash("Email already registered.")
            return redirect(url_for('register'))
        u = User(fullname=fullname, email=email)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash("Registration successful. Login.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.fullname
            flash("Logged in.")
            return redirect(url_for('user_dashboard'))
        flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/dashboard', endpoint='user_dashboard')
def user_dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    reports = user.reports
    return render_template('dashboard.html', user=user, reports=reports)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for('index'))

@app.route('/report', methods=['GET','POST'])
def report():
    if not session.get('user_id'):
        flash("Please login to submit a report.")
        return redirect(url_for('login'))
    if request.method == 'POST':
        description = request.form.get('description')
        severity = request.form.get('severity', 'Low')
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        try:
            lat = float(lat); lon = float(lon)
        except (TypeError, ValueError):
            flash("Invalid location. Use the map to pick location.")
            return redirect(url_for('report'))
        file = request.files.get('image')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        r = Report(
            farmer_id = session['user_id'],
            description = description,
            image_filename = filename,
            latitude = lat,
            longitude = lon,
            severity = severity
        )
        db.session.add(r)
        db.session.commit()
        alert, count = check_for_alerts(lat, lon)
        if alert:
            flash(f"ALERT: {count} reports near this location in last 24h.")
        else:
            flash("Report submitted.")
        return redirect(url_for('thanks'))
    return render_template('report.html')

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

# Admin
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == app.config.get('ADMIN_PASSWORD'):
            session['admin'] = True
            flash("Admin logged in.")
            return redirect(url_for('admin_dashboard'))
        flash("Wrong admin password.")
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('admin_dashboard.html', reports=reports)

@app.route('/admin/toggle_verify/<int:report_id>', methods=['POST'])
def admin_toggle_verify(report_id):
    if not session.get('admin'):
        return jsonify({"error":"unauthorized"}), 403
    r = Report.query.get(report_id)
    if not r:
        return jsonify({"error":"not found"}), 404
    r.verified = not r.verified
    db.session.commit()
    return jsonify({"success": True, "verified": r.verified})

@app.route('/admin/feedback/<int:report_id>', methods=['POST'])
def admin_feedback(report_id):
    if not session.get('admin'):
        flash("Unauthorized")
        return redirect(url_for('admin_login'))
    r = Report.query.get(report_id)
    if not r:
        flash("Report not found")
        return redirect(url_for('admin_dashboard'))
    fb = request.form.get('feedback', '')
    status = request.form.get('status', r.status)
    r.admin_feedback = fb
    r.status = status
    db.session.commit()
    flash("Feedback saved.")
    return redirect(url_for('admin_dashboard'))

@app.route('/api/reports')
def api_reports():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    data = []
    for r in reports:
        data.append({
            "id": r.id,
            "user": r.farmer.fullname if r.farmer else "Unknown",
            "description": r.description,
            "image": url_for('uploaded_file', filename=r.image_filename) if r.image_filename else None,
            "lat": r.latitude,
            "lon": r.longitude,
            "severity": r.severity,
            "verified": r.verified,
            "status": r.status,
            "admin_feedback": r.admin_feedback,
            "created_at": r.created_at.isoformat()
        })
    return jsonify(data)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# error handler
@app.errorhandler(500)
def internal_error(e):
    app.logger.error(f"Server error: {e}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # For local dev only: secret key from env or config
    app.run(debug=True, host='0.0.0.0')
