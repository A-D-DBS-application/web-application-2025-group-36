# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config
from .models import db
import os

migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Zorg dat SQLALCHEMY_DATABASE_URI altijd de Supabase/Postgres URL gebruikt
    # (vul DATABASE_URL in .env of config)
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL is not configured. Set it in Config or environment.")

    # Upload map aanmaken als die nog niet bestaat
    os.makedirs(app.config.get("UPLOAD_FOLDER", "static/papers"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        # Blueprint registreren
        from .routes import main
        app.register_blueprint(main)

        # CLI helper, alleen indien je demo wilt seeden
        # (kan ook verwijderd worden als je geen demo wilt)
        # @app.cli.command("seed_demo")
        # def seed_demo():
        #     from .routes import ensure_demo_content
        #     ensure_demo_content()
        #     print("Demo content ensured.")

    return app
