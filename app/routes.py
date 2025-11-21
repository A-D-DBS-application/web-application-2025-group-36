# app/routes.py

from flask import Blueprint, request, redirect, url_for, render_template, session
from .models import db, User, Company, Paper, Review, PaperCompany

main = Blueprint('main', __name__)


# ---------------------------------------------------
# HOME PAGE
# ---------------------------------------------------
@main.route("/")
def index():
    return render_template("home.html", title="Home")


# ---------------------------------------------------
# VISION PAGE
# ---------------------------------------------------
@main.route("/vision")
def vision():
    return render_template("vision.html", title="Vision")


# ---------------------------------------------------
# ABOUT US PAGE
# ---------------------------------------------------
@main.route("/about")
def about():
    return render_template("about.html", title="About Us")


# ---------------------------------------------------
# LOGIN PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@main.route("/login")
def login():
    return render_template("login.html", title="Login")


# ---------------------------------------------------
# REGISTER PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@main.route("/register")
def register():
    return render_template("register.html", title="Register")



# ---------------------------------------------------
# TEST DATABASE CONNECTION
# ---------------------------------------------------
@main.route("/test_db")
def test_db():
    try:
        users = User.query.all()
        return f"DB werkt! Aantal users in tabel User: {len(users)}"
    except Exception as e:
        return f"Fout bij DB-verbinding: {e}"