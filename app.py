# app.py
import os
from flask import (
    Flask, render_template, redirect, url_for, request, flash, send_from_directory, session
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Report
from functools import wraps

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # init DB
    db.init_app(app)

    # create all tables on first startup
    with app.app_context():
        db.create_all()

    # helpers
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def admin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("is_admin"):
                flash("Admin login required.", "error")
                return redirect(url_for("admin_login"))
            return f(*args, **kwargs)
        return decorated

    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in first.", "error")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated

    # Routes
    @app.route("/")
    def index():
        return render_template("welcome.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            fullname = request.form.get("fullname", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not fullname or not email or not password:
                flash("Fill all required fields.", "error")
                return redirect(url_for("register"))
            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "error")
                return redirect(url_for("register"))
            user = User(
                fullname=fullname,
                email=email,
                password_hash=generate_password_hash(password),
                role="farmer"
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                session.clear()
                session["user_id"] = user.id
                session["user_name"] = user.fullname
                flash("Login successful.", "success")
                return redirect(url_for("user_dashboard", user_id=user.id))
            else:
                flash("Invalid credentials.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "success")
        return redirect(url_for("index"))

    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            pwd = request.form.get("password", "")
            if pwd == app.config["ADMIN_PASSWORD"]:
                session.clear()
                session["is_admin"] = True
                session["user_name"] = "Admin"
                flash("Admin login successful.", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Invalid admin password.", "error")
        return render_template("admin_login.html")

    @app.route("/user/<int:user_id>/dashboard")
    @login_required
    def user_dashboard(user_id):
        # extra check: a logged-in user should only see their dashboard (simple)
        if session.get("user_id") != user_id and not session.get("is_admin"):
            flash("Unauthorized.", "error")
            return redirect(url_for("index"))
        user = User.query.get_or_404(user_id)
        reports = user.reports
        return render_template("dashboard.html", user=user, reports=reports)

    @app.route("/report/new/<int:user_id>", methods=["GET", "POST"])
    @login_required
    def new_report(user_id):
        if session.get("user_id") != user_id and not session.get("is_admin"):
            flash("Unauthorized.", "error")
            return redirect(url_for("index"))
        user = User.query.get_or_404(user_id)
        if request.method == "POST":
            title = request.form.get("title", "Untitled")
            description = request.form.get("description", "")
            lat = request.form.get("latitude")
            lon = request.form.get("longitude")
            try:
                lat_val = float(lat) if lat else None
                lon_val = float(lon) if lon else None
            except ValueError:
                lat_val = lon_val = None

            photo = request.files.get("photo")
            filename = None
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                photo.save(save_path)

            report = Report(
                title=title,
                description=description,
                photo_filename=filename,
                latitude=lat_val,
                longitude=lon_val,
                user=user
            )
            db.session.add(report)
            db.session.commit()
            flash("Report submitted. Thank you!", "success")
            return redirect(url_for("user_dashboard", user_id=user.id))
        return render_template("report.html", user=user)

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/admin/dashboard")
    @admin_required
    def admin_dashboard():
        reports = Report.query.order_by(Report.created_at.desc()).all()
        users_count = User.query.count()
        reports_count = Report.query.count()
        verified_count = Report.query.filter_by(status="verified").count()
        return render_template(
            "admin_dashboard.html",
            reports=reports,
            counts={"users": users_count, "reports": reports_count},
            verified_count=verified_count
        )

    @app.route("/admin/database")
    @admin_required
    def admin_database():
        # an admin-only DB viewer page
        users = User.query.order_by(User.created_at.desc()).all()
        reports = Report.query.order_by(Report.created_at.desc()).all()
        return render_template("admin_database.html", users=users, reports=reports)

    @app.route("/admin/report/<int:report_id>/feedback", methods=["POST"])
    @admin_required
    def admin_feedback(report_id):
        feedback = request.form.get("feedback", "")
        status = request.form.get("status", "")
        report = Report.query.get_or_404(report_id)
        report.admin_feedback = feedback
        if status:
            report.status = status
        db.session.commit()
        flash("Feedback saved.", "success")
        return redirect(url_for("admin_dashboard"))

    # error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    return app

# produce app variable expected by gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
