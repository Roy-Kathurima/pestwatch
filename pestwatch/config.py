import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")
    # Use DATABASE_URL for production (Render/Heroku). SQLite fallback:
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL",
                                            "sqlite:///" + os.path.join(BASE_DIR, "pestwatch.db"))
    # psycopg2 style URL fix if needed: handled upstream when setting env
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB
