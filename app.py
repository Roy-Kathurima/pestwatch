# app.py
import os
from flask import (
    Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Report, LoginEvent

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    with app.app_context():
        # Create tables if they don't exist
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
            user = User.query.filter_by(email=email).first()

            # record login attempt (will set user_id if found)
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            success = False
            user_id = None
            if user and check_password_hash(user.password_hash, password):
                success = True
                user_id = user.id

            le = LoginEvent(user_id=user_id, email=email, ip_address=ip, success=success)
            db.session.add(le)
            db.session.commit()

            if success:
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
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Invalid admin password.", "error")
        return render_template("admin_login.html")

   @app.route("/user/<int:user_id>/dashboard")
def user_dashboard(user_id):
    user = User.query.get_or_404(user_id)

    # Convert reports into JSON-safe format
    reports = [{
        "lat": r.latitude,
        "lng": r.longitude,
        "pest": r.pest_name,
        "desc": r.description,
        "date": r.created_at.strftime("%Y-%m-%d %H:%M")
    } for r in user.reports]

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
        flash("Report updated.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.route("/admin/database", methods=["GET", "POST"])
    def admin_database():
        # On GET show password form OR if ?pwd=... (legacy) check it
        if request.method == "POST":
            pwd = request.form.get("password", "")
            if pwd != app.config["ADMIN_PASSWORD"]:
                flash("Wrong admin password.", "error")
                return redirect(url_for("admin_login"))
            # show DB
            users = User.query.order_by(User.created_at.desc()).all()
            reports = Report.query.order_by(Report.created_at.desc()).all()
            logins = LoginEvent.query.order_by(LoginEvent.created_at.desc()).all()
            return render_template("admin_database.html", users=users, reports=reports, logins=logins)
        else:
            pwd = request.args.get("pwd", "")
            if pwd == app.config["ADMIN_PASSWORD"]:
                users = User.query.order_by(User.created_at.desc()).all()
                reports = Report.query.order_by(Report.created_at.desc()).all()
                logins = LoginEvent.query.order_by(LoginEvent.created_at.desc()).all()
                return render_template("admin_database.html", users=users, reports=reports, logins=logins)
            # show password entry form (reuse admin_login)
            return render_template("admin_login.html")

    # error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template("500.html"), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

