from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import User, Report

admin = Blueprint("admin", __name__, url_prefix="/admin")

def admin_only():
    if not current_user.is_admin:
        return False
    return True

@admin.route("/dashboard")
@login_required
def dashboard():
    if not admin_only(): return "403 Forbidden", 403
    reports = Report.query.all()
    return render_template("admin_dashboard.html", reports=reports)

@admin.route("/users")
@login_required
def users():
    if not admin_only(): return "403 Forbidden", 403
    return render_template("admin_users.html", users=User.query.all())

@admin.route("/view/<int:id>")
@login_required
def view(id):
    if not admin_only(): return "403 Forbidden", 403
    return render_template("admin_view_report.html", report=Report.query.get_or_404(id))
