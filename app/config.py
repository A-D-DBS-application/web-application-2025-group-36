import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = '9e4a1f6c2b8d4f0a7c3e9bd12a4f8c6e5d1f0a3b7e9c4d2f1a6b3c8e7d9f2a1'
    
    # --- DATABASE ---
    raw_db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.ebokqkhwotfewvpsfemj:3R9TrLYvLG7lIx7Y@aws-1-eu-west-1.pooler.supabase.com:6543/postgres"
    )
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- GEMINI ---
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # --- FILE UPLOAD SETTINGS ---
    # Max grootte voor PDF (bijv. 10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 

    # --- SUPABASE KEYS (NIEUW) ---
    # Ik heb ze hier hardcoded ingezet zodat het direct werkt, 
    # maar idealiter zet je dit ook in een .env bestand later.
    SUPABASE_URL = "https://ebokqkhwotfewvpsfemj.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVib2txa2h3b3RmZXd2cHNmZW1qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE2NDI0MTgsImV4cCI6MjA3NzIxODQxOH0.axbpHICgCwwvdRQVlLYDOjtAdvFN3HknkixG3KWanMw"
    
    # Naam van de bucket in Supabase Storage
    SUPABASE_BUCKET = "thesis-pdfs"