# app/config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = '9e4a1f6c2b8d4f0a7c3e9bd12a4f8c6e5d1f0a3b7e9c4d2f1a6b3c8e7d9f2a1'
    
    # -----------------------------
    # DATABASE CONFIG
    # -----------------------------
    # Load DATABASE_URL from Render or from .flaskenv (for local dev)
    raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.ebokqkhwotfewvpsfemj:3R9TrLYvLG7lIx7Y@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"
    )

    # Fix postgres:// issue on some systems
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # -----------------------------
    # Gemini API KEY
    # -----------------------------
    # Gemini API key
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    if not GEMINI_API_KEY:
        print("⚠️ WARNING: GEMINI_API_KEY not set. AI will not work.")

    # -----------------------------
    # FILE UPLOAD SETTINGS
    # -----------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "papers")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
