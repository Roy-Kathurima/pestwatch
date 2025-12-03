PestWatch - Farmer pest reporting app (SQLite)

How to deploy:
1. Paste files into GitHub repo (use File Explorer to create files).
2. On Render, create a Web Service pointing at your repo.
3. Build command: (Render defaults are fine). Start command: gunicorn app:app
4. (Optional) Set ADMIN_UNLOCK_CODE env var in Render to change admin secret.

Admin secret default: admin123

Notes:
- Uses SQLite database file pestwatch.db in project root.
- Uploaded images stored in uploads/ (ephemeral on Render).
- To persist uploads use S3 in future.
