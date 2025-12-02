\# PestWatch



Simple Flask app (farmers report pests). Features:

\- Farmers register/login, submit reports with photo + geolocation

\- Interactive Leaflet maps

\- Admin approval, login logs and CSV export

\- No command-line needed to create admin: /make\_admin?user=USERNAME



Deploy: push to GitHub, connect repo to Render, set build to pip install -r requirements.txt and start as `gunicorn app:app`.



