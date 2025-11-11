from flask import Flask
from .config import Config
from .models import db  # now safe, because db is defined inside models.py
from .routes import bp

def create_app():
    """
    Application factory:
    - maakt de Flask-app
    - laadt config
    - registreert routes (blueprint)
    """
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    # Blueprints registreren (alle routes komen uit routes.py)
    app.register_blueprint(bp)

    # Debug: toon welke routes geladen zijn
    # (handig zolang we ontwikkelen)
    print("✅ Geregistreerde routes:")
    print(app.url_map)

    return app