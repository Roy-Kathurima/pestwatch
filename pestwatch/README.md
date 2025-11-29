# Pest Watch (Flask)

1. Create virtualenv and activate:
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate

2. Install:
   pip install -r requirements.txt

3. Create uploads:
   mkdir -p static/uploads

4. Run locally:
   python app.py
   Visit http://127.0.0.1:5000

Admin account auto-created on first run:
  username: admin
  password: admin123

Change password immediately (create new admin user) in production.

To deploy on Render:
- Set Root Directory to project root (or to the subfolder if you place files under one)
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Provide DATABASE_URL in env if using Postgres
