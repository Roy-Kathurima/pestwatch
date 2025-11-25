# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # secret key for forms+sessions
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Uploads folder (make sure it exists or will be created)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(basedir, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Database URL: prefer environment DATABASE_URL (Render / Heroku style)
    DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI") or ""
    if DATABASE_URL:
        # If Render gives 'postgres://', SQLAlchemy may want 'postgresql://'
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # fallback to sqlite for local dev
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "pestwatch.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Admin password (for admin login). Set in Render as environment variable ADMIN_PASSWORD.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # change in production

    # Optional: default email to seed (not used unless you want)
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@example.com")
