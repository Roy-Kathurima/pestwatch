# app.py
import os
from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, User, Report

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
            fullname = request.form["fullname"].strip()
            email = request.form["email"].strip().lower()
            password = request.form["password"]

            if User.query.filter_by(email=email).first():
                flash("Email already registered.")
                return redirect(url_for("register"))

            user = User(
                fullname=fullname,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()

            flash("Registration successful.")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]

            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password_hash, password):
                return redirect(url_for("user_dashboard", user_id=user.id))

            flash("Invalid credentials.")

        return render_template("login.html")

    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            if request.form["password"] == app.config["ADMIN_PASSWORD"]:
                return redirect(url_for("admin_dashboard"))
            flash("Wrong admin password")

        return render_template("admin_login.html")

    @app.route("/user/<int:user_id>/dashboard")
    def user_dashboard(user_id):
        user = User.query.get_or_404(user_id)
        return render_template("dashboard.html", user=user, reports=user.reports)

    @app.route("/report/new/<int:user_id>", methods=["GET", "POST"])
    def new_report(user_id):
        user = User.query.get_or_404(user_id)

        if request.method == "POST":
            title = request.form["title"]
            description = request.form["description"]

            photo = request.files.get("photo")
            filename = None

            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            report = Report(
                title=title,
                description=description,
                photo_filename=filename,
                user=user
            )

            db.session.add(report)
            db.session.commit()

            flash("Report submitted.")
            return redirect(url_for("user_dashboard", user_id=user.id))

        return render_template("report.html", user=user)

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/admin/dashboard")
    def admin_dashboard():
        users = User.query.count()
        reports = Report.query.all()
        return render_template("admin_dashboard.html", users_count=users, reports=reports)

    @app.route("/admin/database")
    def admin_database():
        pwd = request.args.get("pwd")
        if pwd != app.config["ADMIN_PASSWORD"]:
            flash("Admin password required")
            return redirect(url_for("admin_login"))
        return render_template("admin_database.html",
                               users=User.query.all(),
                               reports=Report.query.all())

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
