from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Report, LoginLog
from config import Config
from datetime import datetime
import csv, io, os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()

# Default route → Login
@app.route("/")
def index():
    return redirect("/login")

# Register
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"]),
            security_question=request.form["question"],
            security_answer=request.form["answer"],
            role="farmer"
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created!")
        return redirect("/login")
    return render_template("register.html")

# Login
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.username
            session["role"] = user.role
            db.session.add(LoginLog(username=user.username))
            db.session.commit()
            return redirect("/dashboard")
        else:
            flash("Invalid login")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Reset Password
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.security_answer == request.form["answer"]:
            user.password = generate_password_hash(request.form["password"])
            db.session.commit()
            flash("Password reset!")
            return redirect("/login")
        else:
            flash("Wrong info")
    return render_template("reset_password.html")

# Farmer Dashboard
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    reports = Report.query.filter_by(approved=True).order_by(Report.created.desc()).all()
    return render_template("dashboard.html", reports=reports)

# Submit Report
@app.route("/farmer_report", methods=["GET","POST"])
def farmer_report():
    if "user" not in session:
        return redirect("/login")
    if request.method == "POST":
        rpt = Report(
            pest=request.form["pest"],
            location=request.form["location"],
            latitude=request.form["lat"],
            longitude=request.form["lon"],
            description=request.form["description"]
        )
        db.session.add(rpt)
        db.session.commit()
        flash("Report submitted")
        return redirect("/dashboard")
    return render_template("farmer_report.html")

# Farmer Reports View
@app.route("/farmer_reports")
def farmer_reports():
    if "user" not in session:
        return redirect("/login")
    reports = Report.query.all()
    return render_template("farmer_reports.html", reports=reports)

# Admin Unlock Page
@app.route("/admin_unlock", methods=["GET","POST"])
def admin_unlock():
    if request.method == "POST":
        if request.form["secret"] == "pestadmin2025":
            session["admin"] = True
            return redirect("/admin")
    return render_template("admin_unlock.html")

# Admin Panel
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin_unlock")
    reports = Report.query.all()
    return render_template("admin.html", reports=reports)

# Approve
@app.route("/approve/<int:id>")
def approve(id):
    if not session.get("admin"):
        return redirect("/admin_unlock")
    rpt = Report.query.get(id)
    rpt.approved = True
    db.session.commit()
    return redirect("/admin")

# Export CSV
@app.route("/export")
def export():
    if not session.get("admin"):
        return redirect("/admin_unlock")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Pest","Location","Lat","Lon","Approved","Date"])

    for r in Report.query.all():
        writer.writerow([r.id,r.pest,r.location,r.latitude,r.longitude,r.approved,r.created])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    output.close()

    return send_file(mem, as_attachment=True, download_name="reports.csv", mimetype="text/csv")
