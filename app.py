import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from models import db, User, Report
from config import Config
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, asin
import csv
import io

ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # Create DB tables if INIT_DB set or if local sqlite and file missing
    with app.app_context():
        if app.config.get('INIT_DB_ON_START'):
            db.create_all()

        # auto-create sqlite DB if using sqlite and file not present (convenience)
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
            db.create_all()

    # ----- Error handler for 500 so we show a friendly page (and not crash)
    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Server Error: {e}, path: {request.path}")
        return render_template('500.html'), 500

    # ---------- Routes ----------
    @app.route('/')
    def index():
        return render_template('welcome.html')

    @app.route('/register', methods=['GET','POST'])
    def register():
        if request.method == 'POST':
            fullname = request.form['fullname']
            email = request.form['email']
            password = request.form['password']
            if User.query.filter_by(email=email).first():
                flash("Email already exists.")
                return redirect(url_for('register'))
            user = User(fullname=fullname, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please login.")
            return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['user_name'] = user.fullname
                flash("Login successful.")
                return redirect(url_for('dashboard'))
            flash("Invalid email or password.")
        return render_template('login.html')

    @app.route('/dashboard')
    def dashboard():
        if not session.get('user_id'):
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        reports = user.reports
        return render_template('dashboard.html', user=user, reports=reports)

    @app.route('/logout')
    def logout():
        session.clear()
        flash("Logged out successfully.")
        return redirect(url_for('index'))

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

    @app.route('/report', methods=['GET','POST'])
    def report():
        if not session.get('user_id'):
            flash("Please login to submit a report.")
            return redirect(url_for('login'))
        if request.method == 'POST':
            description = request.form.get('description')
            lat = request.form.get('latitude')
            lon = request.form.get('longitude')
            severity = request.form.get('severity', 'Low')

            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                flash("Please select a valid location on the map.")
                return redirect(url_for('report'))

            file = request.files.get('image')
            filename = None
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            r = Report(
                farmer_id=session['user_id'],
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
                flash(f"ALERT: {count} reports in this area in the last 24 hours!")
            else:
                flash("Report submitted successfully.")
            return redirect(url_for('thanks'))

        return render_template('report.html')

    @app.route('/thanks')
    def thanks():
        return render_template('thanks.html')

    # --- Admin routes ---
    @app.route('/admin/login', methods=['GET','POST'])
    def admin_login():
        if request.method == 'POST':
            password = request.form['password']
            if password == app.config['ADMIN_PASSWORD']:
                session['admin'] = True
                return redirect(url_for('admin_dashboard'))
            flash("Wrong password.")
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
            flash("Unauthorized.")
            return redirect(url_for('admin_login'))
        feedback = request.form.get('feedback')
        status = request.form.get('status', None)
        severity = request.form.get('severity', None)
        r = Report.query.get(report_id)
        if not r:
            flash("Report not found.")
            return redirect(url_for('admin_dashboard'))
        r.admin_feedback = feedback
        if status:
            r.status = status
        if severity:
            r.severity = severity
        db.session.commit()
        flash("Feedback saved.")
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/export')
    def admin_export():
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        reports = Report.query.order_by(Report.created_at.desc()).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id","farmer","email","description","severity","verified","status","lat","lon","created_at"])
        for r in reports:
            writer.writerow([r.id, r.farmer.fullname if r.farmer else '', r.farmer.email if r.farmer else '',
                             r.description, r.severity, r.verified, r.status, r.latitude, r.longitude, r.created_at])
        output.seek(0)
        return (output.read(), 200, {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=reports.csv"
        })

    # API
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

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    return app

# If run directly
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')
