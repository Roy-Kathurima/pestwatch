from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash
import os

app = create_app()
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    # Optionally create an example user for testing (email unique)
    test_email = os.environ.get('TEST_USER_EMAIL')
    if test_email:
        if not User.query.filter_by(email=test_email).first():
            u = User(
                fullname=os.environ.get('TEST_USER_NAME', 'Test Farmer'),
                email=test_email,
                password_hash=generate_password_hash(os.environ.get('TEST_USER_PASSWORD', 'testpass'))
            )
            db.session.add(u)
            db.session.commit()
            print(f"Created test user {test_email}")
    print("Done.")
