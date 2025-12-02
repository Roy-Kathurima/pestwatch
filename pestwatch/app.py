from flask import Flask, render_template, request, redirect, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Report, LoginLog
from config import Config
import csv

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# CREATE DATABASE
with app.app_context():
    db.create_all()


# ---------- HOME ----------
@app.route("/")
def home():
    reports = Report.query.filter_by(approved=True).all()
    return render_template("index.html", reports=reports)


# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        user = User(username=request.form["username"])
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"]).first()
        success = False

        if u and u.check_password(request.form["password"]):
            login_user(u)
            success = True
            if u.is_admin:
                redirect_page = "/admin"
            else:
                redirect_page = "/dashboard"
        else:
            flash("Invalid login")

        db.session.add(LoginLog(username=request.form["username"], success=success))
        db.session.commit()

        if success:
            return redirect(redirect_page)

    return render_template("login.html")


# ---------- FARMER DASHBOARD ----------
@app.route("/dashboard")
@login_required
def dashboard():
    reports = Report.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", reports=reports)


# ---------- REPORT ----------
@app.route("/report", methods=["GET","POST"])
@login_required
def report():
    if request.method == "POST":
        r = Report(
            title=request.form["title"],
            details=request.form["details"],
            lat=request.form["lat"],
            lng=request.form["lng"],
            user_id=current_user.id
        )
        db.session.add(r)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("farmer_report.html")


# ---------- ADMIN ----------
@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        return "Unauthorized", 403

    reports = Report.query.filter_by(approved=False).all()
    return render_template("admin.html", reports=reports)


@app.route("/approve/<int:id>")
@login_required
def approve(id):
    if not current_user.is_admin:
        return "Unauthorized", 403

    r = Report.query.get(id)
    r.approved = True
    db.session.commit()
    return redirect("/admin")


# ---------- LOGIN LOG ----------
@app.route("/admin/logs")
@login_required
def logs():
    if not current_user.is_admin:
        return "Unauthorized", 403

    logs = LoginLog.query.order_by(LoginLog.time.desc()).all()
    return render_template("admin_logins.html", logs=logs)


# ---------- EXPORT ----------
@app.route("/admin/export")
@login_required
def export():
    if not current_user.is_admin:
        return "Unauthorized", 403

    file = "export.csv"
    with open(file,"w",newline="") as f:
        w = csv.writer(f)
        w.writerow(["User","Success","Time"])
        for l in LoginLog.query.all():
            w.writerow([l.username, l.success, l.time])

    return send_file(file, as_attachment=True)


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")
