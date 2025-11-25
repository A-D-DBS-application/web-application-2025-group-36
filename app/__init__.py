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

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from .routes import main
        app.register_blueprint(main)

        # CLI helper to seed demo data into the currently configured database
        @app.cli.command("seed_demo")
        def seed_demo():
            """Seed the demo papers/companies/reviews in the active database."""
            from .routes import ensure_demo_content
            ensure_demo_content()
            print("Demo content ensured.")

    return app

