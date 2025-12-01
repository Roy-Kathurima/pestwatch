from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Report, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required():
    return current_user.is_authenticated and current_user.is_admin

@admin_bp.route("/")
@login_required
def index():
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin_dashboard.html", reports=reports)

@admin_bp.route("/users")
@login_required
def users():
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))
    users = User.query.filter_by(is_admin=False).order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)

@admin_bp.route("/user/<int:uid>/toggle", methods=["POST"])
@login_required
def toggle_user(uid):
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))
    u = User.query.get_or_404(uid)
    u.is_active = not u.is_active
    db.session.commit()
    flash("User updated", "success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/report/<int:rid>")
@login_required
def view_report(rid):
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))
    r = Report.query.get_or_404(rid)
    return render_template("admin_view_report.html", r=r)

@admin_bp.route("/report/<int:rid>/delete", methods=["POST"])
@login_required
def delete_report(rid):
    if not admin_required():
        flash("Access denied", "danger")
        return redirect(url_for("auth.login"))
    r = Report.query.get_or_404(rid)
    # remove image file
    if r.image:
        try:
            import os
            from flask import current_app
            os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], r.image))
        except:
            pass
    db.session.delete(r)
    db.session.commit()
    flash("Report deleted", "info")
    return redirect(url_for("admin.dashboard"))
