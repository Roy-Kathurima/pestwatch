import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-please-change')
    # If DATABASE_URL provided (Render Postgres), SQLAlchemy will use it. Otherwise local SQLite file.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        "sqlite:///pestwatch.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')
