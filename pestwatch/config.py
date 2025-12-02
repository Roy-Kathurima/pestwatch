import os
BASE = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = "CHANGE_THIS"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE,"database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "uploads"
