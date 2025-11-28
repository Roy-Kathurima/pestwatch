# run: python manage.py create_admin
import sys
from getpass import getpass
from app import app
from models import db, User

def create_admin():
    username = input("Admin username: ").strip()
    pw = getpass("Admin password: ")
    with app.app_context():
        if User.query.filter_by(username=username).first():
            print("User exists.")
            return
        u = User(username=username, role="admin")
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()
        print("Admin user created.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage.py create_admin")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "create_admin":
        create_admin()
    else:
        print("Unknown command")
