import os
from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
from config import Config
from models import db, User
from auth import auth
from admin import admin

app = Flask(__name__)
app.config.from_object(Config)

# ensure uploads folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth)
app.register_blueprint(admin)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads/<filename>")
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.before_first_request
def create_tables():
    db.create_all()

    admin = User.query.filter_by(email="admin@pestwatch.com").first()
    if not admin:
        admin = User(name="Admin", email="admin@pestwatch.com",
                     password=generate_password_hash("admin123"), is_admin=True)
        db.session.add(admin)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
