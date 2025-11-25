# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import create_engine, text
from .config import Config
from .models import db
import os


migrate = Migrate()


def choose_database_uri():
    """Pick the best available DB URI, falling back to SQLite if the primary is unreachable."""
    from .config import DEFAULT_SQLITE

    primary = os.getenv("DATABASE_URL")
    if not primary:
        return f"sqlite:///{DEFAULT_SQLITE}"

    # Try to connect quickly; if it fails, fall back silently to SQLite
    try:
        engine = create_engine(primary, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return primary
    except Exception as exc:
        print(f"[WARN] Cannot reach primary DB, using local SQLite fallback. Error: {exc}")
        return f"sqlite:///{DEFAULT_SQLITE}"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["SQLALCHEMY_DATABASE_URI"] = choose_database_uri()

    # Ensure SQLite directory exists when using fallback/local DB
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
        sqlite_path = app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "", 1)
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)

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
