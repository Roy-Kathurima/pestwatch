from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "secret123"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'pestwatch.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===========================
# MODELS
# ===========================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10))
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    reports = db.relationship('Report', backref='user', lazy=True)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pest = db.Column(db.String(100))
    description = db.Column(db.String(255))
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# ===========================
# HOME
# ===========================
@app.route("/")
def home():
    return render_template("index.html")


# ===========================
# REGISTER
# ===========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        user = User(name=name, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


# ===========================
# LOGIN
# ===========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "admin":
                return redirect("/admin/dashboard")
            else:
                return redirect(f"/user/{user.id}/dashboard")

    return render_template("login.html")


# ===========================
# USER DASHBOARD
# ===========================
@app.route("/user/<int:user_id>/dashboard")
def user_dashboard(user_id):
    user = User.query.get_or_404(user_id)

    reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()

    reports_data = []
    for r in reports:
        reports_data.append({
            "pest": r.pest,
            "desc": r.description,
            "lat": r.latitude,
            "lng": r.longitude,
            "date": r.created_at.strftime("%Y-%m-%d %H:%M")
        })

    return render_template("dashboard.html", user=user, reports=reports_data)


# ===========================
# NEW REPORT
# ===========================
@app.route("/report/new/<int:user_id>", methods=["GET", "POST"])
def new_report(user_id):
    if request.method == "POST":
        pest = request.form['pest']
        desc = request.form['description']
        lat = request.form.get("latitude")
        lng = request.form.get("longitude")

        report = Report(
            pest=pest,
            description=desc,
            latitude=lat,
            longitude=lng,
            user_id=user_id
        )

        db.session.add(report)
        db.session.commit()

        return redirect(f"/user/{user_id}/dashboard")

    return render_template("new_report.html", user_id=user_id)


# ===========================
# ADMIN LOGIN
# ===========================
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form["password"]

        if pwd == "admin123":
            session["admin"] = True
            return redirect("/admin/dashboard")

    return render_template("admin_login.html")


# ===========================
# ADMIN DASHBOARD
# ===========================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect("/admin-login")

    reports = Report.query.all()

    return render_template("admin_dashboard.html", reports=reports)


# ===========================
# ADMIN DATABASE PAGE
# ===========================
@app.route("/admin/database")
def admin_database():
    if not session.get("admin"):
        return redirect("/admin-login")

    users = User.query.all()

    return render_template("admin_database.html", users=users)


# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
