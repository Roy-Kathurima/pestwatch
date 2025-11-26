import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIG ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
# Use DATABASE_URL env var if present (render/Heroku), otherwise sqlite for local dev
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///pestwatch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # role: "farmer" or "admin"
    role = db.Column(db.String(30), default='farmer', nullable=False)
    reports = db.relationship('Report', backref='user', lazy='dynamic')

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)           # keep nullable to allow old rows if any
    description = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(300), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), default='pending')
    admin_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'photo_filename': self.photo_filename,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status,
            'admin_feedback': self.admin_feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user_id': self.user_id
        }

class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120))
    success = db.Column(db.Boolean)
    role = db.Column(db.String(30))
    ip = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- HELPERS ---
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            uid = session.get('user_id')
            if not uid:
                return redirect(url_for('login'))
            user = User.query.get(uid)
            if not user:
                session.clear()
                return redirect(url_for('login'))
            if role and user.role != role:
                flash("Unauthorized", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

# ----- Register -----
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') or 'farmer'

        if not (fullname and email and password):
            flash('Please fill all fields', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        user = User(fullname=fullname, email=email, role=role)
        user.set_password(password)
        db.session.add(user); db.session.commit()
        flash('Account created. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ----- Login (farmer) -----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        ip = request.remote_addr

        user = User.query.filter_by(email=email).first()
        success = False
        role = None
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            success = True
            role = user.role
            flash('Logged in', 'success')
            db.session.add(LoginLog(email=email, success=True, role=role, ip=ip))
            db.session.commit()
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard', user_id=user.id))
        else:
            db.session.add(LoginLog(email=email, success=False, role=user.role if user else None, ip=ip))
            db.session.commit()
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

# ----- Admin Login page (separate) -----
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, role='admin').first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = 'admin'
            flash('Admin logged in', 'success')
            db.session.add(LoginLog(email=email, success=True, role='admin', ip=request.remote_addr))
            db.session.commit()
            return redirect(url_for('admin_dashboard'))
        else:
            db.session.add(LoginLog(email=email, success=False, role='admin', ip=request.remote_addr))
            db.session.commit()
            flash('Invalid admin credentials', 'danger')
            return redirect(url_for('admin_login'))
    return render_template('admin-login.html')

# ----- Logout -----
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('index'))

# ----- Admin dashboard -----
@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    # list reports and include coords for map
    reports = Report.query.order_by(Report.created_at.desc()).all()
    reports_data = [r.to_dict() for r in reports]
    # login logs
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).limit(200).all()
    return render_template('admin_dashboard.html', reports=reports_data, logs=logs)

# ----- Admin database page (shows login logs and users) -----
@app.route('/admin/database')
@login_required(role='admin')
def admin_database():
    # show all users and login logs
    users = User.query.order_by(User.created_at.desc()).all()
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).all()
    return render_template('admin_database.html', users=users, logs=logs)

# ----- User (farmer) dashboard -----
@app.route('/user/<int:user_id>/dashboard')
@login_required()
def user_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    # ensure session matches user (or admin)
    if session.get('user_id') != user.id and session.get('role') != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    # get reports for user
    reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    reports_data = [r.to_dict() for r in reports]
    return render_template('dashboard.html', user=user, reports=reports_data, leaflet_api_key=None)

# ----- Create new report (shows form) -----
@app.route('/report/new/<int:user_id>', methods=['GET', 'POST'])
@login_required()
def new_report(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        lat = request.form.get('latitude') or None
        lon = request.form.get('longitude') or None
        # simple photo handling: just store filename (if you plan to implement real upload, adapt)
        photo_filename = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename:
                # save to static/uploads (ensure folder exists)
                upload_dir = os.path.join('static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                filename = f"{int(datetime.utcnow().timestamp())}_{photo.filename}"
                path = os.path.join(upload_dir, filename)
                photo.save(path)
                photo_filename = filename

        # coerce coordinates
        try:
            lat_f = float(lat) if lat else None
            lon_f = float(lon) if lon else None
        except ValueError:
            lat_f = lon_f = None

        report = Report(
            title=title,
            description=description,
            photo_filename=photo_filename,
            latitude=lat_f,
            longitude=lon_f,
            user_id=user.id
        )
        db.session.add(report)
        db.session.commit()
        flash('Report submitted', 'success')
        return redirect(url_for('user_dashboard', user_id=user.id))
    return render_template('report_new.html', user=user)

# ----- Initialize DB (use once) -----
@app.route('/init-db')
def init_db():
    # Create tables if missing; also create default admin if not exists
    db.create_all()
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@pestwatch.local')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpass')
    if not User.query.filter_by(email=admin_email).first():
        admin = User(fullname='Administrator', email=admin_email, role='admin')
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
    return "DB initialized and admin created (if missing)."

# --- Error handlers for nicer debug messages ---
@app.errorhandler(500)
def internal_error(e):
    # in production don't reveal stacktrace
    return render_template('500.html', error=str(e)), 500

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

# --- Run (for local dev) ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
