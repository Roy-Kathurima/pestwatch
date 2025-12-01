import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# -------------------------------
# APP SETUP
# -------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret123"

# Database
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///pestwatch.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# Login System
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# -------------------------------
# DATABASE MODELS
# -------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(250))
    is_admin = db.Column(db.Boolean, default=False)
    reports = db.relationship("Report", backref="farmer", lazy=True)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pest_name = db.Column(db.String(120))
    description = db.Column(db.Text)
    location = db.Column(db.String(120))
    latitude = db.Column(db.String(40))
    longitude = db.Column(db.String(40))
    image = db.Column(db.String(200))
    farmer_id = db.Column(db.Integer, db.ForeignKey("user.id"))


# -------------------------------
# LOGIN MANAGER
# -------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------------------
# IMAGE SAVE HELPER
# -------------------------------
def save_uploaded_image(file):
    if not file or not file.filename:
        return None

    filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    return filename


# -------------------------------
# ROUTES
# -------------------------------

@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        password = generate_password_hash(request.form["password"])
        user = User(
            name=request.form["name"],
            email=request.form["email"],
            password=password
        )
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form["email"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            if user.is_admin:
                return redirect("/admin")
            return redirect("/dashboard")
        flash("Invalid login")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.filter_by(farmer_id=current_user.id).all()
    return render_template("dashboard.html", reports=reports)


# -------------------------------
# SUBMIT REPORT
# -------------------------------
@app.route("/report", methods=["POST"])
@login_required
def submit_report():
    file = request.files.get("image")
    filename = save_uploaded_image(file)

    report = Report(
        pest_name=request.form["pest"],
        description=request.form["description"],
        location=request.form["location"],
        latitude=request.form["latitude"],
        longitude=request.form["longitude"],
        image=filename,
        farmer_id=current_user.id
    )
    db.session.add(report)
    db.session.commit()

    flash("Report submitted successfully")
    return redirect("/dashboard")


# -------------------------------
# ADMIN DASHBOARD
# -------------------------------
@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        return redirect("/dashboard")

    reports = Report.query.all()
    return render_template("admin.html", reports=reports)


@app.route("/admin/report/<int:rid>")
@login_required
def admin_report(rid):
    report = Report.query.get_or_404(rid)
    return render_template("admin_report.html", r=report)


@app.route("/admin/users")
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect("/dashboard")

    users = User.query.all()
    return render_template("admin_users.html", users=users)


# -------------------------------
# SERVE UPLOADED FILES
# -------------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# -------------------------------
# DEBUG VIEW (DELETE AFTER TESTING)
# -------------------------------
@app.route("/debug/list_uploads")
def list_uploads():
    return jsonify(os.listdir(app.config["UPLOAD_FOLDER"]))


# -------------------------------
# LOGOUT
# -------------------------------
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")


# -------------------------------
# CREATE DATABASE + DEFAULT ADMIN
# -------------------------------
@app.before_first_request
def create_tables():
    db.create_all()

    admin = User.query.filter_by(email="admin@pestwatch.com").first()
    if not admin:
        admin = User(
            name="Admin",
            email="admin@pestwatch.com",
            password=generate_password_hash("admin123"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Default Admin Created")
        print("EMAIL: admin@pestwatch.com")
        print("PASSWORD: admin123")


# -------------------------------
# RUN APP
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
