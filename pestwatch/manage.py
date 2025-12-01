# usage: python manage.py create_admin
import sys
from getpass import getpass
from app import app
from models import db, User
from werkzeug.security import generate_password_hash

def create_admin():
    username = input("Username: ").strip() or "admin"
    email = input("Email: ").strip() or "admin@pestwatch.com"
    password = getpass("Password: ")
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print("User exists.")
            return
        u = User(username=username, email=email, is_admin=True,
                 password_hash=generate_password_hash(password))
        db.session.add(u)
        db.session.commit()
        print("Admin created.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage.py create_admin")
        sys.exit(1)
    if sys.argv[1] == "create_admin":
        create_admin()
    else:
        print("Unknown command")
