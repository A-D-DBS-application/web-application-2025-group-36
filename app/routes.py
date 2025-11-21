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
# SEARCH PAPERS – iedereen mag kijken
# ---------------------------------------------------
@main.route("/search_papers")
def search_papers():
    papers = Paper.query.all()
    return render_template("search_papers.html", title="Search Papers", papers=papers)


# ---------------------------------------------------
# UPLOAD PAPER – alleen Researcher
# ---------------------------------------------------
@main.route("/upload_paper", methods=["GET", "POST"])
def upload_paper():
    # Moet ingelogd zijn
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    # Moet Researcher zijn
    if session.get("user_role") != "Researcher":
        return render_template("error_role.html", title="Access denied", required="Researcher")

    if request.method == "POST":
        title = request.form.get("title")
        abstract = request.form.get("abstract")

        if not title or not abstract:
            flash("Fill in all fields.", "error")
            return redirect(url_for("main.upload_paper"))

        paper = Paper(
            title=title,
            abstract=abstract,
            user_id=session.get("user_id")
        )
        db.session.add(paper)
        db.session.commit()
        flash("Paper uploaded successfully.", "success")
        return redirect(url_for("main.search_papers"))

    # GET: formulier tonen
    return render_template("upload_paper.html", title="Upload Paper")

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
    return redirect(url_for("main.index"))



# ---------------------------------------------------
# LOGIN PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")

        # user zoeken
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No account found with this email.", "error")
            return redirect(url_for("main.login"))

        # user in session plaatsen
        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role

        # Redirect naar home!
        return redirect(url_for("main.index"))

    # GET -> login formulier tonen
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

        # bestaat email al?
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already exists.", "error")
            return redirect(url_for("main.register"))

        # nieuwe user
        user = User(name=name, email=email, role=role)
        db.session.add(user)
        db.session.commit()

        # login na registreren
        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role

        # redirect naar home
        return redirect(url_for("main.index"))

    # GET → formulier tonen
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