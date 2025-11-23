import os
from flask import Flask, render_template, redirect, request, session, url_for, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Report
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    # Create tables on first run (important for Render Postgres)
    with app.app_context():
        db.create_all()

    # -----------------------
    # ROUTES
    # -----------------------

    @app.route("/")
    def home():
        return render_template("welcome.html")

    # ------------------------------------
    # USER REGISTRATION
    # ------------------------------------
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            fullname = request.form["fullname"]
            email = request.form["email"]
            password = request.form["password"]

            existing = User.query.filter_by(email=email).first()
            if existing:
                flash("Email already registered.", "danger")
                return redirect(url_for("register"))

            hashed = generate_password_hash(password)
            user = User(fullname=fullname, email=email, password_hash=hashed)
            db.session.add(user)
            db.session.commit()

            flash("Account created! Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    # ------------------------------------
    # USER & ADMIN LOGIN
    # ------------------------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"]
            password = request.form["password"]

            # Admin login
            if email == "admin@pestwatch.com":
                if password == os.getenv("ADMIN_PASSWORD", "admin123"):
                    session["admin"] = True
                    flash("Admin login successful!", "success")
                    return redirect(url_for("admin_dashboard"))
                else:
                    flash("Incorrect admin password.", "danger")
                    return redirect(url_for("login"))

            # Farmer login
            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid email or password!", "danger")
                return redirect(url_for("login"))

            session["user_id"] = user.id
            session["fullname"] = user.fullname

            return redirect(url_for("dashboard"))

        return render_template("login.html")

    # ------------------------------------
    # FARMER DASHBOARD
    # ------------------------------------
    @app.route("/dashboard")
    def dashboard():
        if "user_id" not in session:
            return redirect(url_for("login"))

        return render_template("dashboard.html", fullname=session.get("fullname"))

    # ------------------------------------
    # SUBMIT REPORT
    # ------------------------------------
    @app.route("/report", methods=["GET", "POST"])
    def report():
        if "user_id" not in session:
            return redirect(url_for("login"))

        if request.method == "POST":
            pest_type = request.form["pest_type"]
            severity = request.form["severity"]
            description = request.form["description"]
            latitude = request.form["latitude"]
            longitude = request.form["longitude"]

            photo = request.files["photo"]
            filename = None
            if photo:
                filename = datetime.now().strftime("%Y%m%d%H%M%S_") + photo.filename
                photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            new_report = Report(
                user_id=session["user_id"],
                pest_type=pest_type,
                severity=severity,
                description=description,
                latitude=latitude,
                longitude=longitude,
                photo=filename,
                created_at=datetime.now()
            )

            db.session.add(new_report)
            db.session.commit()

            return render_template("thanks.html")

        return render_template("report.html")

    # ------------------------------------
    # ADMIN DASHBOARD
    # ------------------------------------
    @app.route("/admin/dashboard")
    def admin_dashboard():
        if not session.get("admin"):
            return redirect(url_for("login"))

        reports = Report.query.order_by(Report.created_at.desc()).all()
        return render_template("admin_dashboard.html", reports=reports)

    # ------------------------------------
    # ADMIN SEND FEEDBACK (stores inside DB)
    # ------------------------------------
    @app.route("/admin/feedback/<int:report_id>", methods=["POST"])
    def admin_feedback(report_id):
        if not session.get("admin"):
            return redirect(url_for("login"))

        feedback_text = request.form["feedback"]

        report = Report.query.get_or_404(report_id)
        report.admin_feedback = feedback_text
        db.session.commit()

        flash("Feedback sent successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    # ------------------------------------
    # LOGOUT
    # ------------------------------------
    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("home"))

    # ------------------------------------
    # Serve uploaded photos
    # ------------------------------------
    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app


# Run local server
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
