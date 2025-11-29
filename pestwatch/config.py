import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(basedir, "pestwatch.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB uploads
    ALERT_WINDOW_DAYS = int(os.environ.get("ALERT_WINDOW_DAYS", 7))
    ALERT_RADIUS_KM = float(os.environ.get("ALERT_RADIUS_KM", 5.0))
    ALERT_THRESHOLD = int(os.environ.get("ALERT_THRESHOLD", 3))
