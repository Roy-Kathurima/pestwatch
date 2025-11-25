import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from config import Config
from models import db, User, Report
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from io import StringIO
import csv
from datetime import datetime

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    db.init_app(app)

    @app.route('/')
    def index():
        # public landing/welcome page
        return render_template('welcome.html')

    # --------------------
    # User registration + login (simple session-based)
    # --------------------
    @app.route('/register', methods=['GET','POST'])
    def register():
        if request.method == 'POST':
            name = request.form.get('fullname')
            email = request.form.get('email')
            password = request.form.get('password')
            if not name or not email or not password:
                flash('Please fill all fields')
                return redirect(url_for('register'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered')
                return redirect(url_for('register'))
            u = User(fullname=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(u)
            db.session.commit()
            flash('Registration successful. Please login.')
            return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            # find user
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['user_name'] = user.fullname
                flash('Logged in successfully.')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials.')
                return redirect(url_for('login'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Logged out.')
        return redirect(url_for('index'))

    # --------------------
    # User Dashboard (my reports)
    # --------------------
    @app.route('/dashboard')
    def dashboard():
        uid = session.get('user_id')
        if not uid:
            flash('Please login first.')
            return redirect(url_for('login'))
        user = User.query.get(uid)
        reports = Report.query.filter_by(user_id=uid).order_by(Report.created_at.desc()).all()
        return render_template('dashboard.html', user=user, reports=reports)

    # --------------------
    # Submit report page
    # --------------------
    @app.route('/report', methods=['GET','POST'])
    def report():
        uid = session.get('user_id')
        if request.method == 'POST':
            title = request.form.get('title')
            desc = request.form.get('description')
            pest_type = request.form.get('pest_type')
            severity = request.form.get('severity')
            lat = request.form.get('latitude') or None
            lon = request.form.get('longitude') or None
            file = request.files.get('image')
            filename = None
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            r = Report(
                title=title,
                description=desc,
                pest_type=pest_type,
                severity=severity,
                image_filename=filename,
                latitude=float(lat) if lat else None,
                longitude=float(lon) if lon else None,
                user_id=uid
            )
            db.session.add(r)
            db.session.commit()
            flash('Report submitted, thank you.')
            return redirect(url_for('dashboard') if uid else url_for('index'))
        # GET
        return render_template('report.html')

    # --------------------
    # Admin login + dashboard
    # --------------------
    @app.route('/admin/login', methods=['GET','POST'])
    def admin_login():
        if request.method == 'POST':
            pwd = request.form.get('password')
            if pwd == app.config['ADMIN_PASSWORD']:
                session['is_admin'] = True
                return redirect(url_for('admin_dashboard'))
            flash('Wrong admin password')
            return redirect(url_for('admin_login'))
        return render_template('admin_login.html')

    @app.route('/admin/logout')
    def admin_logout():
        session.pop('is_admin', None)
        flash('Admin logged out')
        return redirect(url_for('index'))

    @app.route('/admin/dashboard')
    def admin_dashboard():
        if not session.get('is_admin'):
            flash('Admin only.')
            return redirect(url_for('admin_login'))
        # show summary and all reports
        reports = Report.query.order_by(Report.created_at.desc()).all()
        total = len(reports)
        verified_count = Report.query.filter_by(verified=True).count()
        return render_template('admin_dashboard.html', reports=reports, total=total, verified_count=verified_count)

    # Admin: mark verified / feedback
    @app.route('/admin/report/<int:report_id>/verify', methods=['POST'])
    def admin_verify(report_id):
        if not session.get('is_admin'):
            return ('Forbidden', 403)
        r = Report.query.get_or_404(report_id)
        r.verified = request.form.get('verified') == 'true'
        r.admin_feedback = request.form.get('feedback', r.admin_feedback)
        db.session.commit()
        return jsonify({'status':'ok'})

    # Admin: export CSV of reports
    @app.route('/admin/export/reports')
    def admin_export_reports():
        if not session.get('is_admin'):
            flash('Admin only.'); return redirect(url_for('admin_login'))
        reports = Report.query.order_by(Report.created_at.desc()).all()
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['id','title','description','pest_type','severity','lat','lon','user_id','created_at','verified','admin_feedback'])
        for r in reports:
            cw.writerow([r.id, r.title, r.description, r.pest_type, r.severity, r.latitude, r.longitude, r.user_id, r.created_at.isoformat(), r.verified, r.admin_feedback or ''])
        output = si.getvalue()
        return send_file(
            StringIO(output),
            mimetype='text/csv',
            as_attachment=True,
            download_name='reports.csv'
        )

    # Admin: view raw DB page (simple table) — only admin can see
    @app.route('/admin/db')
    def admin_db_page():
        if not session.get('is_admin'):
            flash('Admin only.'); return redirect(url_for('admin_login'))
        users = User.query.order_by(User.created_at.desc()).all()
        reports = Report.query.order_by(Report.created_at.desc()).all()
        return render_template('admin_db.html', users=users, reports=reports)

    # serve uploaded images (optional)
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        # do not leak e in production
        return render_template('500.html'), 500

    return app

# Standalone run
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
