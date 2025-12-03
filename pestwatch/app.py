from flask import Flask, render_template, request, redirect, session, url_for, send_file
from models import db, User, Report, LoginLog
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from io import StringIO
import csv
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- HOME -------------------
@app.route("/")
def home():
    return redirect("/login")


# ---------------- AUTH --------------------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"]),
            question=request.form["question"],
            answer=request.form["answer"]
        )
        db.session.add(user)
        db.session.commit()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.username

            log = LoginLog(username=user.username)
            db.session.add(log)
            db.session.commit()

            return redirect("/dashboard")
        return "Invalid login"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- DASHBOARD -----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# ------------- RESET PASSWORD ---------------
@app.route("/reset", methods=["GET","POST"])
def reset():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.answer == request.form["answer"]:
            user.password = generate_password_hash(request.form["new"])
            db.session.commit()
            return redirect("/login")
        return "Verification failed"
    return render_template("reset_password.html")


# ---------------- REPORT --------------------
@app.route("/report", methods=["GET","POST"])
def report():
    if request.method == "POST":
        r = Report(
            pest=request.form["pest"],
            location=request.form["location"],
            lat=request.form["lat"],
            lon=request.form["lon"]
        )
        db.session.add(r)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("farmer_report.html")


@app.route("/reports")
def reports():
    data = Report.query.all()
    return render_template("farmer_reports.html", data=data)


# -------------- ADMIN ---------------
@app.route("/admin-unlock", methods=["GET","POST"])
def admin_unlock():
    if request.method == "POST":
        if request.form["code"] == app.config["ADMIN_UNLOCK_CODE"]:
            session["admin"] = True
            return redirect("/admin")
    return render_template("admin_unlock.html")


@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect("/admin-unlock")
    data = Report.query.all()
    return render_template("admin.html", data=data)


@app.route("/approve/<int:id>")
def approve(id):
    r = Report.query.get(id)
    r.status = "Approved"
    db.session.commit()
    return redirect("/admin")


# ------------ LOGIN LOGS ------------
@app.route("/admin-logins")
def admin_logins():
    logs = LoginLog.query.order_by(LoginLog.timestamp.desc()).all()
    return render_template("admin_logins.html", logs=logs)


# ----------- EXPORT DB -------------
@app.route("/export")
def export():
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["ID","Pest","Location","Status"])
    for r in Report.query.all():
        writer.writerow([r.id, r.pest, r.location, r.status])
    stream.seek(0)
    return send_file(stream, as_attachment=True, download_name="reports.csv", mimetype="text/csv")


# -------- ERROR ----------
@app.errorhandler(404)
def notfound(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run()
