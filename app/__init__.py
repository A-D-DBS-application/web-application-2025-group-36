from flask import Flask
from .routes import bp  # blueprint met alle routes

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