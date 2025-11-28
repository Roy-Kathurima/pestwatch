import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import json

# Configuration
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "replace-this-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///pestwatch.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ----------------------
# Database Models
# ----------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="farmer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Report(db.Model):
    __tablename__ = "reports"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(40), default="pending")
    admin_feedback = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class LoginLog(db.Model):
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(200), nullable=True)
    ip = db.Column(db.String(100), nullable=True)
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# ----------------------
# Helpers
# ----------------------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def reports_to_dictlist(reports):
    out = []
    for r in reports:
        out.append({
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "photo_url": (url_for("static", filename=f"uploads/{r.photo_filename}") if r.photo_filename else None),
            "latitude": r.latitude,
            "longitude": r.longitude,
            "status": r.status,
            "admin_feedback": r.admin_feedback,
            "created_at": r.created_at.isoformat(),
            "user_id": r.user_id
        })
    return out


# ----------------------
# Routes
# ----------------------
@app.route("/")
def home():
    return render_template("welcome.html", user=current_user())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        email = request.form.get("email")
        password = request.form.get("password")

        if not (fullname and email and password):
            flash("Please fill all fields", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "warning")
            return redirect(url_for("register"))

        u = User(fullname=fullname, email=email, password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        log = LoginLog(user_id=(user.id if user else None), email=email, ip=request.remote_addr)

        if user and user.check_password(password):
            session["user_id"] = user.id
            log.success = True
            flash("Logged in", "success")
            return redirect(url_for("user_dashboard", user_id=user.id))
        else:
            log.success = False
            flash("Invalid credentials", "danger")
            return redirect(url_for("login"))

        db.session.add(log)
        db.session.commit()

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out", "info")
    return redirect(url_for("home"))


@app.route("/user/<int:user_id>/dashboard")
def user_dashboard(user_id):
    user = User.query.get_or_404(user_id)
    reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
    return render_template("dashboard.html", user=user, reports=reports_to_dictlist(reports))


@app.route("/report/new/<int:user_id>", methods=["GET", "POST"])
def report_new(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        lat = request.form.get("latitude")
        lon = request.form.get("longitude")
        file = request.files.get("photo")
        filename = None

        if file and file.filename:
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        r = Report(
            title=title or "No title",
            description=description,
            photo_filename=filename,
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None,
            user_id=user.id
        )

        db.session.add(r)
        db.session.commit()
        flash("Report submitted", "success")
        return redirect(url_for("user_dashboard", user_id=user.id))

    return render_template("report_new.html", user=user)


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ✅ ADMIN LOGIN (FIXED)
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password")
        admin_pwd = os.environ.get("ADMIN_PWD", "adminpass")

        if pwd == admin_pwd:
            session["is_admin"] = True
            flash("Admin logged in", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Bad admin password", "danger")
            return redirect(url_for("admin_login"))

    # ✅ FIXED TEMPLATE NAME
    return render_template("admin_login.html")


@app.route("/admin-logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out", "info")
    return redirect(url_for("home"))


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("is_admin"):
        flash("Admin login required", "warning")
        return redirect(url_for("admin_login"))

    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin-dashboard.html", reports=reports_to_dictlist(reports))


@app.route("/admin/database")
def admin_database():
    if not session.get("is_admin"):
        flash("Admin login required", "warning")
        return redirect(url_for("admin_login"))

    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).limit(500).all()
    users = User.query.order_by(User.created_at.desc()).all()
    reports = Report.query.order_by(Report.created_at.desc()).all()

    return render_template("admin-database.html", logs=logs, users=users, reports=reports)


@app.route("/report/<int:report_id>")
def view_report(report_id):
    r = Report.query.get_or_404(report_id)
    return render_template("report_view.html", report=r)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
