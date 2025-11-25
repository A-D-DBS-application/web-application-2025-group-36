# app/config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = '9e4a1f6c2b8d4f0a7c3e9bd12a4f8c6e5d1f0a3b7e9c4d2f1a6b3c8e7d9f2a1'
    
    # Supabase Postgres URI, via environment variable of direct hardcoded
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:3R9TrLYvLG7lIx7Y@db.ebokqkhwotfewvpsfemj.supabase.co:5432/postgres"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload folder voor PDF papers
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "papers")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB limit
