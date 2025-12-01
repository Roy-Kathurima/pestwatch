import os
import time
from flask import Flask, render_template, url_for, send_from_directory
from flask_migrate import Migrate
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from config import Config
from models import db, User
from auth import auth_bp
from admin import admin_bp

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

# Ensure uploads folder
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# DB init
db.init_app(app)
migrate = Migrate(app, db)

# Login
login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)

# route to serve uploaded files
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# Home index route (optional)
@app.route("/")
def index():
    return render_template("index.html")

# Create tables + default admin at startup
@app.before_first_request
def create_tables_and_admin():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@pestwatch.com",
                     password_hash=generate_password_hash("admin123"),
                     is_admin=True)
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Created default admin: admin / admin123")

if __name__ == "__main__":
    app.run(debug=True)
