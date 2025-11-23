import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    # If DATABASE_URL is set (Render/Postgres), use it. Otherwise use local sqlite file.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{BASE_DIR / 'pestwatch.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload folder default (guaranteed to exist at app startup)
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or str(BASE_DIR / 'static' / 'uploads')
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB

    # Admin password (set via env var on Render)
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')

    # Helper flag: when set to '1' in env on first deploy, the app will create DB tables (one-time)
    INIT_DB_ON_START = os.environ.get('INIT_DB', '0') == '1'
