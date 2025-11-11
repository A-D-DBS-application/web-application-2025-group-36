from flask import Flask
from .routes import bp  # blueprint met alle routes

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    db.init_app(app)
    app.register_blueprint(bp)

    return app
