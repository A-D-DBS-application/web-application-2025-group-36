import os

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")   # Supabase project URL
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")   # Service role key voor server-side toegang
    SECRET_KEY = os.getenv("SECRET_KEY", "supergeheimesleutel")  # Flask secret key
