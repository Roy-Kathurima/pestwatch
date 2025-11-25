# app.py
import os
from flask import (
    Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
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

    # create all tables on first startup (safe for small/demo apps)
    with app.app_context():
        db.create_all()

    # helpers
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def admin_required(f):
        """Simple admin protection decorator using ADMIN_PASSWORD in session/args (demo)."""
        @wraps(f)
        def decorated(*args, **kwargs):
            # For demo, check query param or form or header (not secure for prod)
            token = request.args.get("pwd") or request.form.get("admin_password") or request.headers.get("X-ADMIN-PWD")
            if token != app.config["ADMIN_PASSWORD"]:
                flash("Admin password required.", "error")
                return redirect(url_for("admin_login"))
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
                # Demo: no sessions; redirect to user dashboard using id in URL
                flash("Login successful.", "success")
                return redirect(url_for("user_dashboard", user_id=user.id))
            else:
                flash("Invalid credentials.", "error")
        return render_template("login.html")

    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            pwd = request.form.get("password", "")
            if pwd == app.config["ADMIN_PASSWORD"]:
                return redirect(url_for("admin_dashboard", pwd=pwd))
            else:
                flash("Invalid admin password.", "error")
        return render_template("admin_login.html")

    @app.route("/user/<int:user_id>/dashboard")
    def user_dashboard(user_id):
        user = User.query.get_or_404(user_id)
        reports = user.reports
        return render_template("dashboard.html", user=user, reports=reports)

    @app.route("/report/new/<int:user_id>", methods=["GET", "POST"])
    def new_report(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == "POST":
            title = request.form.get("title", "Untitled")
            description = request.form.get("description", "")
            lat = request.form.get("latitude")
            lon = request.form.get("longitude")
            lat_val = float(lat) if lat else None
            lon_val = float(lon) if lon else None

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

    @app.route("/uploads/<filename>")
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
            verified_count=verified_count,
            pwd=request.args.get("pwd", "")
        )

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
        return redirect(url_for("admin_dashboard", pwd=request.form.get("admin_password", "")))

    @app.route("/admin/database")
    @admin_required
    def admin_database():
        # admin-only DB browser page
        users = User.query.order_by(User.created_at.desc()).all()
        reports = Report.query.order_by(Report.created_at.desc()).all()
        return render_template("admin_database.html", users=users, reports=reports, pwd=request.args.get("pwd", ""))

    # Small init route to create/drop tables and seed admin (ONLY use once then remove)
    @app.route("/init-db", methods=["GET", "POST"])
    def init_db_route():
        """
        Usage (very carefully):
        - Send POST with form field 'action' = 'create' or 'drop' and 'admin_password' = ADMIN_PASSWORD
        Example (curl):
        curl -X POST https://your-app/init-db -d "action=create" -d "admin_password=YOUR_ADMIN_PASSWORD"
        """
        if request.method == "POST":
            action = request.form.get("action")
            pwd = request.form.get("admin_password", "")
            if pwd != app.config["ADMIN_PASSWORD"]:
                return "Unauthorized", 403
            if action == "drop":
                db.drop_all(app=app)
                return "Dropped all tables", 200
            elif action == "create":
                db.create_all(app=app)
                # create default admin (if not exists)
                admin_email = app.config.get("DEFAULT_ADMIN_EMAIL", "admin@example.com")
                if not User.query.filter_by(email=admin_email).first():
                    admin = User(
                        fullname="Admin",
                        email=admin_email,
                        password_hash=generate_password_hash(pwd),
                        role="admin"
                    )
                    db.session.add(admin)
                    db.session.commit()
                return "Created tables and seeded admin", 200
            else:
                return "Invalid action", 400
        return render_template("init_db.html")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        # return simple 500 page
        return render_template("500.html"), 500

    return app

# expose app for gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
