import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key")  # fallback if not set
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{os.getenv('USER')}:{os.getenv('PASSWORD')}"
        f"@{os.getenv('HOST')}:{os.getenv('PORT')}/{os.getenv('DBNAME')}?sslmode=require"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

DUMMY_PAPERS = []
DUMMY_COMPANIES = []
LINKS = {}