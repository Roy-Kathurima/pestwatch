import os, pandas
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Report, LoginLog
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

os.makedirs("uploads", exist_ok=True)

login = LoginManager(app)
login.login_view = "login"

@login.user_loader
def load(uid):
    return User.query.get(int(uid))

def log(name, ok):
    l = LoginLog(username=name, ip=request.remote_addr,
                 agent=request.headers.get("User-Agent"), success=ok)
    db.session.add(l)
    db.session.commit()
with app.app_context():
    db.create_all()


@app.route("/")
def home():
    reports = Report.query.filter_by(approved=True).all()
    return render_template("index.html", reports=reports)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        u = User(username=request.form["username"])
        u.set_password(request.form["password"])
        db.session.add(u)
        db.session.commit()
        flash("Registered")
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login_page():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form["username"]).first()
        if u and u.check_password(request.form["password"]):
            login_user(u)
            log(u.username, True)
            return redirect("/")
        log(request.form["username"], False)
        flash("Invalid")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/report", methods=["GET","POST"])
@login_required
def report():
    if request.method == "POST":
        f = request.files["image"]
        name = ""
        if f:
            name = secure_filename(f.filename)
            f.save("uploads/" + name)

        r = Report(title=request.form["title"],
                   details=request.form["details"],
                   lat=request.form["lat"],
                   lng=request.form["lng"],
                   image=name,
                   user=current_user)
        db.session.add(r)
        db.session.commit()
        flash("Report submitted for approval")
    return render_template("farmer_report.html")

@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin: return "FORBIDDEN"
    reports = Report.query.all()
    return render_template("admin.html", reports=reports)

@app.route("/approve/<id>")
@login_required
def approve(id):
    if not current_user.is_admin: return "FORBIDDEN"
    r = Report.query.get(id)
    r.approved = True
    db.session.commit()
    return redirect("/admin")

@app.route("/export")
@login_required
def export():
    if not current_user.is_admin: return "FORBIDDEN"
    df = pandas.read_sql_table("report", db.engine)
    file = "reports.csv"
    df.to_csv(file, index=False)
    return send_from_directory(".", file, as_attachment=True)

@app.route("/logs")
@login_required
def logs():
    if not current_user.is_admin: return "FORBIDDEN"
    logs = LoginLog.query.all()
    return render_template("logs.html", logs=logs)

@app.route("/uploads/<file>")
def img(file):
    return send_from_directory("uploads", file)

