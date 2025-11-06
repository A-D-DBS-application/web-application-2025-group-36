from app import create_app

app = create_app()

if __name__ == "__main__":
    # Start de dev-server
    app.run(debug=True)