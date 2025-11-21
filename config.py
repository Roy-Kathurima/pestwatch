import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "devkey123")

    # PostgreSQL database from Render
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
