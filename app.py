import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

from models import db, User, Report
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Ensure tables exist (Postgres-compatible)
with app.app_context():
    db.create_all()


# ---------------------------
# HOME
# ---------------------------
@app.route("/")
def home():
    return render_template("welcome.html")


# ---------------------------
# USER REGISTRATION
# ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            return "Email already exists"

        user = User(fullname=fullname, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------------------
# USER LOGIN
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return "Invalid credentials"

        session["user_id"] = user.id
        return redirect(url_for("user_dashboard"))

    return render_template("login.html")


# ---------------------------
# USER DASHBOARD
# ---------------------------
@app.route("/dashboard")
def user_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    reports = user.reports

    return render_template("dashboard.html", user=user, reports=reports)


# ---------------------------
# SUBMIT REPORT
# ---------------------------
@app.route("/report", methods=["GET", "POST"])
def report():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        description = request.form["description"]
        severity = request.form.get("severity", "Low")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        image = request.files["image"]
        filename = None
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join("static/uploads", filename))

        new_report = Report(
            description=description,
            severity=severity,
            latitude=latitude,
            longitude=longitude,
            image_filename=filename,
            user_id=session["user_id"],
        )

        db.session.add(new_report)
        db.session.commit()

        return redirect(url_for("user_dashboard"))

    return render_template("submit_report.html")


# ---------------------------
# ADMIN LOGIN
# ---------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form["password"]

        if password == app.config["ADMIN_PASSWORD"]:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "Incorrect admin password"

    return render_template("admin_login.html")


# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin_dashboard.html", reports=reports)


# ---------------------------
# LOGOUT
# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
