from flask import Blueprint, render_template

bp = Blueprint("main", __name__)

# ---------------------------------------------------
# HOME PAGE
# ---------------------------------------------------
@bp.route("/")
def index():
    return render_template("home.html", title="Home")


# ---------------------------------------------------
# VISION PAGE
# ---------------------------------------------------
@bp.route("/vision")
def vision():
    return render_template("vision.html", title="Vision")


# ---------------------------------------------------
# ABOUT US PAGE
# ---------------------------------------------------
@bp.route("/about")
def about():
    return render_template("about.html", title="About Us")


# ---------------------------------------------------
# LOGIN PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@bp.route("/login")
def login():
    return render_template("login.html", title="Login")


# ---------------------------------------------------
# REGISTER PAGE (placeholder – werkt met nieuwe layout)
# ---------------------------------------------------
@bp.route("/register")
def register():
    return render_template("register.html", title="Register")
