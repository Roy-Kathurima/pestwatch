import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    # Use Render DATABASE_URL (set in Render env vars)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///pestwatch.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # UPLOAD_FOLDER: prefer env var, otherwise default to ./static/uploads
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(BASE_DIR, 'static', 'uploads')

    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')
