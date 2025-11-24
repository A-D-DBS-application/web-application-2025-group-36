import os  

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_SQLITE = os.path.join(os.path.abspath(os.path.join(BASE_DIR, "..")), "database", "app.db")


class Config:
    SECRET_KEY = '9e4a1f6c2b8d4f0a7c3e9bd12a4f8c6e5d1f0a3b7e9c4d2f1a6b3c8e7d9f2a1'
    # Use DATABASE_URL env var if provided, otherwise fall back to a local SQLite file
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "papers")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB, bv. voor paper uploads
