# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Uploads
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(basedir, "uploads")
    )

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # DATABASE
    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "pestwatch.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin password
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
