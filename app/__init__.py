from flask import Flask
from .models import db
from .routes import bp

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    db.init_app(app)
    app.register_blueprint(bp)

    return app
