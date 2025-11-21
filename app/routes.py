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
# LOGOUT FUNCTIONALITY
# ---------------------------------------------------
@main.route("/logout")
def logout():
    session.clear()
    flash("Je bent uitgelogd.", "info")
    return redirect(url_for("main.index"))


# ---------------------------------------------------
# LOGIN PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")

        if not email:
            flash("Vul je e-mailadres in.", "error")
            return redirect(url_for("main.login"))

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Geen account gevonden. Maak eerst een account aan.", "error")
            return redirect(url_for("main.register"))

        # inloggen
        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role

        flash(f"Ingelogd als {user.name} ({user.role})", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html", title="Login")



# ---------------------------------------------------
# REGISTER PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role")

        # heel basic checks
        if not name or not email or not role:
            flash("Vul alle velden in.", "error")
            return redirect(url_for("main.register"))

        # bestaat er al een user met die email?
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Er bestaat al een account met dit e-mailadres. Log gewoon in.", "info")
            return redirect(url_for("main.login"))

        # nieuwe user aanmaken
        user = User(name=name, email=email, role=role)
        db.session.add(user)
        db.session.commit()

        # user inloggen via session
        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role

        flash(f"Welkom, {user.name}!", "success")
        return redirect(url_for("main.index"))

    # GET: enkel formulier tonen
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