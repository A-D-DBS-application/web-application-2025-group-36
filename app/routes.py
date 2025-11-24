# app/routes.py
from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app
from .models import db, User, Company, Paper, Review, PaperCompany

from werkzeug.utils import secure_filename
import os
import time


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
    query = request.args.get("q", "").strip()

    if query:
        papers = Paper.query.filter(
            (
                Paper.title.ilike(f"%{query}%") |
                Paper.abstract.ilike(f"%{query}%")
            )
        ).all()
    else:
        papers = Paper.query.all()

    return render_template("search_papers.html", title="Search Papers", papers=papers, query=query)


# ---------------------------------------------------
# HELPERS FUNCTION (UPLOAD PAPERS)
# ---------------------------------------------------
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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
        file = request.files.get("file")

        if not title or not abstract:
            flash("Fill in title and abstract.", "error")
            return redirect(url_for("main.upload_paper"))

        if not file or file.filename == "":
            flash("Please select a PDF file.", "error")
            return redirect(url_for("main.upload_paper"))

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("main.upload_paper"))

        # veilige bestandsnaam
        filename = secure_filename(file.filename)
        # uniek maken (user_id + timestamp)
        unique_name = f"{session.get('user_id')}_{int(time.time())}_{filename}"

        # fysieke opslag
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        full_path = os.path.join(upload_folder, unique_name)
        file.save(full_path)

        # relatieve path opslaan in DB (t.o.v. static/)
        relative_path = f"papers/{unique_name}"

        paper = Paper(
            title=title,
            abstract=abstract,
            user_id=session.get("user_id"),
            file_path=relative_path
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
    
#DIT IS VOOR DE CHANGE-ROLE
@main.route("/change_role", methods=["GET", "POST"])
def change_role():
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    user = User.query.get(session.get("user_id"))

    if request.method == "POST":
        new_role = request.form.get("role")

        if not new_role:
            flash("Choose a valid role.", "error")
            return redirect(url_for("main.change_role"))

        # Update permanent in database
        user.role = new_role
        db.session.commit()

        # Update session
        session["user_role"] = new_role

        flash("Role updated successfully.", "success")
        return redirect(url_for("main.index"))

    # List all available roles
    roles = ["Researcher", "Reviewer", "User", "System/Admin", "Founder"]

    return render_template("change_role.html", title="Change Role", roles=roles, user=user)
# ---------------------------------------------------
# UPDATE PAPER – alleen auteur of admin
# ---------------------------------------------------
@main.route("/update_paper/<int:paper_id>", methods=["GET", "POST"])
def update_paper(paper_id):
    # Moet ingelogd zijn
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    paper = Paper.query.get_or_404(paper_id)

    # Alleen auteur of admin/Founder mag updaten
    if session.get("user_id") != paper.user_id and session.get("user_role") not in ["System/Admin", "Founder"]:
        flash("Access denied.", "error")
        return redirect(url_for("main.search_papers"))

    if request.method == "POST":
        title = request.form.get("title")
        abstract = request.form.get("abstract")

        if not title or not abstract:
            flash("Fill in title and abstract.", "error")
            return redirect(url_for("main.update_paper", paper_id=paper_id))

        # Update database
        paper.title = title
        paper.abstract = abstract
        db.session.commit()

        flash("Paper updated successfully.", "success")
        return redirect(url_for("main.search_papers"))

    # GET: formulier tonen met bestaande data
    return render_template("update_paper.html", paper=paper, title="Update Paper")
@main.route("/paper/<int:paper_id>/delete", methods=["POST"])
def delete_paper(paper_id):
    if not session.get("user_id"):
        return redirect(url_for("main.login"))

    paper = Paper.query.get_or_404(paper_id)

    # Alleen eigenaar of admin/founder
    if session.get("user_id") != paper.user_id and session.get("user_role") not in ["System/Admin", "Founder"]:
        abort(403)

    db.session.delete(paper)
    db.session.commit()

    flash("Paper deleted successfully.", "success")
    return redirect(url_for("main.search_papers"))
