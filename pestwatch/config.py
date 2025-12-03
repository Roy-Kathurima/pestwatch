import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "pestwatch-secret-key-change-me")

    # FORCE SQLITE ALWAYS (IGNORE RENDER DATABASE_URL)
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "pestwatch.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024  # 6 MB
    ADMIN_UNLOCK_CODE = os.environ.get("ADMIN_UNLOCK_CODE", "admin123")
