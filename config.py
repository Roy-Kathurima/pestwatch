import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    # If DATABASE_URL env var is set (Render), use it; otherwise use local sqlite for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(basedir, 'pestwatch.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads folder (ensure exists)
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB

    # Admin password (set on Render environment variables)
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')
