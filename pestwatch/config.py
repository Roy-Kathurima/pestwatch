import os

class Config:
    SECRET_KEY = "pestwatch_secret"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///pestwatch.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
