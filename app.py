import os
from datetime import datetime
from flask import (
    Flask, render_template, redirect, url_for, request, flash,
    send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Report, LoginAttempt

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    # ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # init DB
    db.init_app(app)

    # create all tables on startup if they don't exist
    with app.app_context():
        db.create_all()
        # ensure a seeded admin exists if DEFAULT_ADMIN_EMAIL and ADMIN_PASSWORD provided
        admin_email = app.config.get("DEFAULT_ADMIN_EMAIL")
        admin_pw = app.config.get("ADMIN_PASSWORD", "admin123")
        if admin_email:
            if not User.query.filter_by(email=admin_email).first():
                admin = User(
                    fullname="Administrator",
                    email=admin_email,
                    password_hash=generate_password_hash(admin_pw),
                    role="admin"
                )
                db.session.add(admin)
                db.session.commit()

    # helpers
    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def client_ip():
        # X-Forwarded-For may be present on Render/proxy; fallback to remote_addr
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        return request.remote_addr or "unknown"

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
            success = False
            user_id = None
            if user and check_password_hash(user.password_hash, password):
                success = True
                user_id = user.id
                flash("Login successful.", "success")
                # In this demo we don't implement sessions; redirect to dashboard passing user id
                db.session.add(LoginAttempt(
                    user_id=user_id,
                    email=email,
                    success=True,
                    ip=client_ip(),
                    role_attempt=user.role
                ))
                db.session.commit()
                return redirect(url_for("user_dashboard", user_id=user.id))
            else:
                flash("Invalid credentials.", "error")
                db.session.add(LoginAttempt(
                    user_id=None if not user else user.id,
                    email=email,
                    success=False,
                    ip=client_ip(),
                    role_attempt=(user.role if user else None)
                ))
                db.session.commit()
        return render_template("login.html")

    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            pwd = request.form.get("password", "")
            if pwd == app.config["ADMIN_PASSWORD"]:
                # record login attempt
                db.session.add(LoginAttempt(
                    user_id=None,
                    email=app.config.get("DEFAULT_ADMIN_EMAIL", "admin"),
                    success=True,
                    ip=client_ip(),
                    role_attempt="admin"
                ))
                db.session.commit()
                return redirect(url_for("admin_dashboard"))
            else:
                db.session.add(LoginAttempt(
                    user_id=None,
                    email=request.form.get("email", "admin"),
                    success=False,
                    ip=client_ip(),
                    role_attempt="admin"
                ))
                db.session.commit()
                flash("Invalid admin password.", "error")
        return render_template("admin_login.html")

    @app.route("/user/<int:user_id>/dashboard")
    def user_dashboard(user_id):
        user = User.query.get_or_404(user_id)
        reports = user.reports.order_by(Report.created_at.desc()).all()
        # For map: show all reports (for farmer, we may show only their own; here we show their reports)
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
                filename = secure_filename(f"{datetime.utcnow().timestamp()}_{photo.filename}")
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
    def admin_dashboard():
        # simple admin gate via ADMIN_PASSWORD query param OR default admin seeded user
        pwd = request.args.get("pwd", "")
        # allow admin if password matches or if request came directly after admin-login (demo)
        if pwd and pwd != app.config["ADMIN_PASSWORD"]:
            flash("Invalid admin password.", "error")
            return redirect(url_for("admin_login"))
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

    @app.route("/admin/report/<int:report_id>/feedback", methods=["POST"])
    def admin_feedback(report_id):
        pwd = request.form.get("admin_password", "")
        if pwd != app.config["ADMIN_PASSWORD"]:
            return jsonify({"error": "unauthorized"}), 403
        feedback = request.form.get("feedback", "")
        status = request.form.get("status", "")
        report = Report.query.get_or_404(report_id)
        report.admin_feedback = feedback
        if status:
            report.status = status
        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/database")
    def admin_database():
        # Protect page by ADMIN_PASSWORD param (safer would be sessions; this is a demo)
        pwd = request.args.get("pwd", "")
        if pwd != app.config["ADMIN_PASSWORD"]:
            flash("Admin password required to view database page.", "error")
            return redirect(url_for("admin_login"))
        users = User.query.order_by(User.created_at.desc()).all()
        reports = Report.query.order_by(Report.created_at.desc()).all()
        attempts = LoginAttempt.query.order_by(LoginAttempt.attempted_at.desc()).limit(500).all()
        return render_template("admin_database.html", users=users, reports=reports, attempts=attempts)

    # Reset DB (dangerous) - protected by RESET_DB_SECRET env var. Use only when you want to wipe & recreate schema.
    @app.route("/reset-db", methods=["POST"])
    def reset_db():
        secret = request.args.get("secret", "")
        if secret != app.config.get("RESET_DB_SECRET"):
            abort(404)
        # WARNING: This will DROP ALL TABLES. Use only for forced resets.
        with app.app_context():
            db.drop_all()
            db.create_all()
            # seed admin again
            admin_email = app.config.get("DEFAULT_ADMIN_EMAIL")
            if admin_email:
                admin_pw = app.config.get("ADMIN_PASSWORD", "admin123")
                if not User.query.filter_by(email=admin_email).first():
                    admin = User(
                        fullname="Administrator",
                        email=admin_email,
                        password_hash=generate_password_hash(admin_pw),
                        role="admin"
                    )
                    db.session.add(admin)
                    db.session.commit()
        return jsonify({"status": "ok", "msg": "db reset done"})

    # basic error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    return app


# expose app for gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
