from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Simple home route
@app.route('/')
def index():
    return "Hello, Supabase connected!"

# Route to test DB connection
@app.route('/test-db')
def test_db():
    try:
        with db.engine.connect() as conn:
            result = conn.execute("SELECT NOW();")
            current_time = result.fetchone()[0]
            return f"Database connection successful! Current DB time: {current_time}"
    except Exception as e:
        return f"Failed to connect: {e}"

if __name__ == "__main__":
    # Run Flask server without testing DB on startup
    app.run(debug=True)
