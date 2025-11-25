# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(basedir, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # DB URL precedence: Render/Heroku style env var DATABASE_URL
    DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI") or ""
    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "pestwatch.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
