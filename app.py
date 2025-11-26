import os
from flask import (
    Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Report, LoginLog

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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
            ip = request.remote_addr
            ua = request.headers.get("User-Agent")
            user = User.query.filter_by(email=email).first()
            success = False
            user_id = None
            if user and check_password_hash(user.password_hash, password):
                success = True
                user_id = user.id
                flash("Login successful.", "success")
                db.session.add(LoginLog(user_id=user_id, email=email, success=True, ip=ip, user_agent=ua))
                db.session.commit()
                return redirect(url_for("user_dashboard", user_id=user.id))
            else:
                db.session.add(LoginLog(user_id=None if not user else user.id, email=email, success=False, ip=ip, user_agent=ua))
                db.session.commit()
                flash("Invalid credentials.", "error")
        return render_template("login.html")

    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            pwd = request.form.get("password", "")
            if pwd == app.config["ADMIN_PASSWORD"]:
                flash("Admin login successful.", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Invalid admin password.", "error")
        return render_template("admin_login.html")

    @app.route("/user/<int:user_id>/dashboard")
    def user_dashboard(user_id):
        user = User.query.get_or_404(user_id)
        reports = user.reports
        # pass reports as list of dicts for map markers
        markers = [
            {
                "id": r.id,
                "title": r.title,
                "lat": r.latitude,
                "lon": r.longitude,
                "photo": r.photo_filename
            } for r in reports if r.latitude is not None and r.longitude is not None
        ]
        return render_template("dashboard.html", user=user, reports=reports, markers=markers)

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
            if photo and photo.filename and allowed_file(photo.filename):
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
    def admin_dashboard():
        reports = Report.query.order_by(Report.created_at.desc()).all()
        users_count = User.query.count()
        reports_count = Report.query.count()
        verified_count = Report.query.filter_by(status="verified").count()
        # prepare markers for map (all reports)
        markers = [
            {
                "id": r.id,
                "title": r.title,
                "lat": r.latitude,
                "lon": r.longitude,
                "user_email": r.user.email if r.user else ""
            } for r in reports if r.latitude is not None and r.longitude is not None
        ]
        return render_template(
            "admin_dashboard.html",
            reports=reports,
            counts={"users": users_count, "reports": reports_count},
            verified_count=verified_count,
            markers=markers
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
        pwd = request.args.get("pwd", "")
        if pwd != app.config["ADMIN_PASSWORD"]:
            flash("Admin password required to view database page.", "error")
            return redirect(url_for("admin_login"))
        users = User.query.order_by(User.created_at.desc()).all()
        reports = Report.query.order_by(Report.created_at.desc()).all()
        logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).limit(500).all()
        return render_template("admin_database.html", users=users, reports=reports, logs=logs)

    @app.route("/admin/reset-db", methods=["POST"])
    def admin_reset_db():
        # Danger: use only for reset; require both ADMIN_PASSWORD and RESET_DB_TOKEN env var
        pwd = request.form.get("admin_password", "")
        token = request.form.get("reset_token", "")
        if pwd != app.config["ADMIN_PASSWORD"] or token != app.config.get("RESET_DB_TOKEN"):
            abort(403)
        # Drop and recreate all tables
        db.drop_all(app=app)
        db.create_all(app=app)
        return "DB reset complete", 200

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
