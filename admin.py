from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Report, Alert
from models import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required():
    return current_user.is_authenticated and current_user.role == "admin"

@admin_bp.route("/")
@login_required
def dashboard():
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("index"))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin_dashboard.html", reports=reports)

@admin_bp.route("/users")
@login_required
def users():
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("index"))
    farmers = User.query.filter_by(role="farmer").order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=farmers)

@admin_bp.route("/alerts")
@login_required
def alerts():
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("index"))
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template("admin_alerts.html", alerts=alerts)
