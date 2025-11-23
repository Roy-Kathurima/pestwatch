# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-for-prod")
    # If DATABASE_URL env var exists (Render Postgres), use it; else use SQLite file
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(BASE_DIR, "pestwatch.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads folder (can be overridden by env var)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    # Admin password (override on Render with env var)
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
