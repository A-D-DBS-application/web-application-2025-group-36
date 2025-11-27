# app/routes.py
from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app, abort
from .models import db, User, Company, Paper, Review, PaperCompany

from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from sqlalchemy import extract
from werkzeug.utils import secure_filename
import os
import time
from collections import Counter
from datetime import datetime

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
# Helper Functions (Dashboard)
# ---------------------------------------------------
def get_user_domain_preferences(user):
    """Return normalized preference scores per domain for this user."""
    counts = Counter()
    total = 0

    for review in user.reviews:
        if review.paper and review.paper.research_domain:
            counts[review.paper.research_domain] += 1
            total += 1

    if total == 0:
        return {}  # No history → no preference boost

    return {domain: count / total for domain, count in counts.items()}


def compute_paper_score(paper, user_prefs, score_map, now):
    """Combine personalization, popularity, and recency into one score."""
    # 1. Personalization by domain
    domain = paper.research_domain
    pref_score = user_prefs.get(domain, 0)

    # 2. Popularity (avg review score, normalized between 0-1)
    pop_score = 0
    if paper.paper_id in score_map and score_map[paper.paper_id]["avg"] is not None:
        pop_score = score_map[paper.paper_id]["avg"] / 5.0

    # 3. Recency (1 if today, 0 if older than 30 days)
    days_old = (now - paper.upload_date).days if paper.upload_date else 365
    recency_score = max(0, 1 - (days_old / 30))

    # Weighted final score
    return (
        0.5 * pref_score +
        0.3 * pop_score +
        0.2 * recency_score
    )

# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------
@main.route("/dashboard")
def dashboard():
    search = request.args.get("q", "").strip()
    selected_domain = request.args.get("domain", "all")
    selected_company = request.args.get("company", "").strip()
    min_score = request.args.get("min_score", "").strip()
    sort = request.args.get("sort", "newest")

    avg_subq = (
        db.session.query(
            Review.paper_id.label("paper_id"),
            func.avg(Review.score).label("avg_score"),
            func.count(Review.review_id).label("score_count"),
        )
        .group_by(Review.paper_id)
        .subquery()
    )

    query = Paper.query

    if search:
        query = query.filter(
            or_(
                Paper.title.ilike(f"%{search}%"),
                Paper.abstract.ilike(f"%{search}%"),
                Paper.research_domain.ilike(f"%{search}%"),
            )
        )

    if selected_domain and selected_domain != "all":
        query = query.filter(Paper.research_domain.ilike(f"%{selected_domain}%"))

    if selected_company:
        query = query.join(PaperCompany).join(Company).filter(Company.name.ilike(f"%{selected_company}%"))

    query = query.outerjoin(avg_subq, Paper.paper_id == avg_subq.c.paper_id)

    min_score_val = None
    if min_score:
        try:
            min_score_val = float(min_score)
            query = query.filter(func.coalesce(avg_subq.c.avg_score, 0) >= min_score_val)
        except ValueError:
            min_score_val = None

    if sort == "best":
        query = query.order_by(func.coalesce(avg_subq.c.avg_score, 0).desc())
    else:
        query = query.order_by(Paper.upload_date.desc())

    papers = (
        query.options(
            joinedload(Paper.author),
            joinedload(Paper.reviews).joinedload(Review.reviewer),
            joinedload(Paper.reviews).joinedload(Review.company),
            joinedload(Paper.companies).joinedload(PaperCompany.company),
        )
        .distinct()
        .all()
    )

    avg_rows = db.session.query(avg_subq.c.paper_id, avg_subq.c.avg_score, avg_subq.c.score_count).all()
    score_map = {
        row.paper_id: {
            "avg": round(float(row.avg_score), 1) if row.avg_score is not None else None,
            "count": row.score_count,
        }
        for row in avg_rows
    }

    # ---------------------------------------------------------------------
    #  PERSONALIZED SMART RANKING SYSTEM
    # ---------------------------------------------------------------------
    user_id = session.get("user_id")
    user = User.query.get(user_id) if user_id else None

    if user:
        # 1. compute preferences from past reviews
        prefs = get_user_domain_preferences(user)
        now = datetime.utcnow()

        # 2. compute personalized score for each paper
        scored = [
            (paper, compute_paper_score(paper, prefs, score_map, now))
            for paper in papers
        ]

        # 3. sort papers DESC by personalized score
        scored.sort(key=lambda x: x[1], reverse=True)

        # 4. extract sorted papers
        papers = [p for p, score in scored]

    # domain + company filters
    domain_rows = db.session.query(Paper.research_domain).distinct().all()
    domain_filters = sorted({d.research_domain for d in domain_rows if d.research_domain})
    companies = Company.query.order_by(Company.name).all()

    return render_template(
        "dashboard.html",
        title="Dashboard",
        papers=papers,
        score_map=score_map,
        domains=domain_filters,
        companies=companies,
        selected_domain=selected_domain,
        selected_company=selected_company,
        min_score=min_score_val if min_score_val is not None else "",
        sort=sort,
        query=search,
    )

# ---------------------------------------------------
# SEARCH PAPERS
# ---------------------------------------------------
@main.route("/search_papers")
def search_papers():
    incoming = request.args.get("q", "").strip()
    return redirect(url_for("main.dashboard", q=incoming))

# ---------------------------------------------------
# HELPERS FUNCTION (UPLOAD PAPERS)
# ---------------------------------------------------
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------------------------------------------
# UPLOAD PAPER – alleen Researcher/Admin/Founder
# ---------------------------------------------------
@main.route("/upload_paper", methods=["GET", "POST"])
def upload_paper():
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    # Allow Researcher, Founder, Admin, System
    allowed_roles = ["Researcher", "Founder", "System/Admin"]

    user_role = session.get("user_role")
    if user_role not in allowed_roles:
        return render_template(
            "error_role.html",
            title="Access denied",
            required="Researcher"
        )

    companies = Company.query.order_by(Company.name).all()

    if request.method == "POST":
        title = request.form.get("title")
        abstract = request.form.get("abstract")
        research_domain = request.form.get("research_domain") or "General"
        custom_domain = (request.form.get("custom_domain") or "").strip()
        file = request.files.get("file")
        selected_company_id = request.form.get("company_id")
        new_company_name = (request.form.get("new_company") or "").strip()
        new_company_industry = (request.form.get("new_company_industry") or "").strip()

        if research_domain == "Other" and custom_domain:
            research_domain = custom_domain

        if not title or not abstract:
            flash("Fill in title and abstract.", "error")
            return redirect(url_for("main.upload_paper"))

        if not file or file.filename == "":
            flash("Please select a PDF file.", "error")
            return redirect(url_for("main.upload_paper"))

        if not allowed_file(file.filename):
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("main.upload_paper"))

        filename = secure_filename(file.filename)
        unique_name = f"{session.get('user_id')}_{int(time.time())}_{filename}"
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        full_path = os.path.join(upload_folder, unique_name)
        file.save(full_path)
        relative_path = f"papers/{unique_name}"

        paper = Paper(
            title=title,
            abstract=abstract,
            research_domain=research_domain,
            user_id=session.get("user_id"),
            file_path=relative_path
        )
        db.session.add(paper)
        db.session.flush()

        company_obj = None
        if new_company_name:
            company_obj = Company(name=new_company_name, industry=new_company_industry or None)
            db.session.add(company_obj)
            db.session.flush()
        elif selected_company_id:
            company_obj = Company.query.get(int(selected_company_id))

        if company_obj:
            link_exists = PaperCompany.query.filter_by(
                paper_id=paper.paper_id, company_id=company_obj.company_id
            ).first()
            if not link_exists:
                db.session.add(PaperCompany(paper_id=paper.paper_id, company_id=company_obj.company_id))

        db.session.commit()
        flash("Paper uploaded successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("upload_paper.html", title="Upload Paper", companies=companies)


# ---------------------------------------------------
# PAPER DETAIL + REVIEWS
# ---------------------------------------------------
@main.route("/papers/<int:paper_id>", methods=["GET", "POST"])
def paper_detail(paper_id):
    paper = Paper.query.options(
        joinedload(Paper.author),
        joinedload(Paper.reviews).joinedload(Review.reviewer),
        joinedload(Paper.reviews).joinedload(Review.company),
        joinedload(Paper.companies).joinedload(PaperCompany.company),
    ).get_or_404(paper_id)

    companies = Company.query.order_by(Company.name).all()
    can_review_roles = ["Reviewer", "Company", "System/Admin", "Founder"]
    can_review = session.get("user_role") in can_review_roles

    if request.method == "POST":
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return redirect(url_for("main.login"))

        if not can_review:
            flash("Only reviewers or company users can leave a score/comment.", "error")
            return redirect(url_for("main.paper_detail", paper_id=paper_id))

        score_raw = request.form.get("score")
        comments = (request.form.get("comments") or "").strip()
        company_id = request.form.get("company_id")

        if not score_raw and not comments:
            flash("Add at least a score or a comment.", "error")
            return redirect(url_for("main.paper_detail", paper_id=paper_id))

        score_value = None
        if score_raw:
            try:
                score_value = float(score_raw)
            except ValueError:
                flash("Score must be a number between 0 and 10.", "error")
                return redirect(url_for("main.paper_detail", paper_id=paper_id))
            if score_value < 0 or score_value > 10:
                flash("Score must be between 0 and 10.", "error")
                return redirect(url_for("main.paper_detail", paper_id=paper_id))

        company_obj = None
        if company_id:
            company_obj = Company.query.get(int(company_id))

        review = Review(
            paper_id=paper.paper_id,
            reviewer_id=session.get("user_id"),
            company_id=company_obj.company_id if company_obj else None,
            score=score_value,
            comments=comments,
        )
        db.session.add(review)
        db.session.commit()
        flash("Review gepubliceerd en zichtbaar voor iedereen.", "success")
        return redirect(url_for("main.paper_detail", paper_id=paper.paper_id))

    scored = [r.score for r in paper.reviews if r.score is not None]
    average_score = round(sum(scored) / len(scored), 1) if scored else None
    score_count = len(scored)
    reviews_sorted = sorted(paper.reviews, key=lambda r: r.date_submitted, reverse=True)

    return render_template(
        "paper_detail.html",
        title=paper.title,
        paper=paper,
        companies=companies,
        can_review=can_review,
        average_score=average_score,
        score_count=score_count,
        reviews_sorted=reviews_sorted,
    )

# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------
@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))

# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with this email.", "error")
            return redirect(url_for("main.login"))
        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role
        return redirect(url_for("main.index"))
    return render_template("login.html", title="Login")

# ---------------------------------------------------
# REGISTER
# ---------------------------------------------------
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role")
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "error")
            return redirect(url_for("main.register"))
        user = User(name=name, email=email, role=role)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role
        return redirect(url_for("main.index"))
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

# ---------------------------------------------------
# CHANGE ROLE
# ---------------------------------------------------
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
        user.role = new_role
        db.session.commit()
        session["user_role"] = new_role
        flash("Role updated successfully.", "success")
        return redirect(url_for("main.index"))

    roles = ["Researcher", "Reviewer", "Company", "User", "System/Admin", "Founder"]
    return render_template("change_role.html", title="Change Role", roles=roles, user=user)

# ---------------------------------------------------
# UPDATE PAPER
# ---------------------------------------------------
@main.route("/update_paper/<int:paper_id>", methods=["GET", "POST"])
def update_paper(paper_id):
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    paper = Paper.query.get_or_404(paper_id)
    if session.get("user_id") != paper.user_id and session.get("user_role") not in ["System/Admin", "Founder"]:
        flash("Access denied.", "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        abstract = request.form.get("abstract")
        research_domain = request.form.get("research_domain") or paper.research_domain
        custom_domain = (request.form.get("custom_domain") or "").strip()
        selected_company_id = request.form.get("company_id")
        new_company_name = (request.form.get("new_company") or "").strip()
        new_company_industry = (request.form.get("new_company_industry") or "").strip()

        if research_domain == "Other" and custom_domain:
            research_domain = custom_domain

        paper.title = title
        paper.abstract = abstract
        paper.research_domain = research_domain

        company_obj = None
        if new_company_name:
            company_obj = Company(name=new_company_name, industry=new_company_industry or None)
            db.session.add(company_obj)
            db.session.flush()
        elif selected_company_id:
            company_obj = Company.query.get(int(selected_company_id))

        if company_obj:
            PaperCompany.query.filter_by(paper_id=paper.paper_id).delete()
            db.session.add(PaperCompany(paper_id=paper.paper_id, company_id=company_obj.company_id))

        db.session.commit()
        flash("Paper updated successfully.", "success")
        return redirect(url_for("main.dashboard"))

    companies = Company.query.order_by(Company.name).all()
    return render_template("update_paper.html", paper=paper, title="Update Paper", companies=companies)

# ---------------------------------------------------
# DELETE PAPER
# ---------------------------------------------------
@main.route("/paper/<int:paper_id>/delete", methods=["POST"])
def delete_paper(paper_id):
    if not session.get("user_id"):
        return redirect(url_for("main.login"))

    paper = Paper.query.get_or_404(paper_id)
    if session.get("user_id") != paper.user_id and session.get("user_role") not in ["System/Admin", "Founder"]:
        abort(403)

    db.session.delete(paper)
    db.session.commit()
    flash("Paper deleted successfully.", "success")
    return redirect(url_for("main.dashboard"))

# ---------------------------------------------------
# ADD COMPANY
# ---------------------------------------------------
@main.route("/add_company", methods=["GET", "POST"])
def add_company():
    if not session.get("user_id") or session.get("user_role") not in ["System/Admin", "Founder"]:
        flash("Access denied.", "error")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form.get("name")
        industry = request.form.get("industry")
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("main.add_company"))
        company = Company(name=name, industry=industry)
        db.session.add(company)
        db.session.commit()
        flash("Company added successfully.", "success")
        return redirect(url_for("main.list_companies"))

    return render_template("add_company.html", title="Add Company")

# ---------------------------------------------------
# LIST COMPANIES
# ---------------------------------------------------
@main.route("/companies")
def list_companies():
    companies = Company.query.all()
    return render_template("list_companies.html", title="Companies", companies=companies)

# ---------------------------------------------------
# ABOUT PAGE
# ---------------------------------------------------
@main.route("/about")
def about():
    return render_template("about.html", title="About")

# ---------------------------------------------------
# Profile Page
# ---------------------------------------------------
@main.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("main.login"))

    user = User.query.get(user_id)

    papers_count = len(user.papers)
    reviews_count = len(user.reviews)

    return render_template(
        "profile.html",
        user=user,
        papers_count=papers_count,
        reviews_count=reviews_count
    )

# ---------------------------------------------------
# Edit Profile
# ---------------------------------------------------
@main.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("main.login"))

    user = User.query.get(user_id)

    if request.method == "POST":
        new_name = request.form.get("name").strip()
        new_email = request.form.get("email").strip()

        # Update user object
        user.name = new_name
        user.email = new_email
        db.session.commit()

        # IMPORTANT: update session so navbar updates
        session["user_name"] = user.name
        session["user_email"] = user.email

        flash("Profile updated successfully!", "success")
        return redirect(url_for("main.profile"))

    return render_template("edit_profile.html", user=user, title="Edit Profile")

# ---------------------------------------------------
# Stats (Algorithmic support)
# ---------------------------------------------------
@main.route("/stats")
def stats():
    total_reviews = db.session.query(Review).count()
    total_papers = db.session.query(Paper).count()

    reviews_by_weekday = (
        db.session.query(
            extract('dow', Review.date_submitted).label("weekday"),
            func.count(Review.review_id)
        )
        .group_by(extract('dow', Review.date_submitted))
        .order_by(extract('dow', Review.date_submitted))
        .all()
    )
    weekday_map = {int(day): count for day, count in reviews_by_weekday}

    papers_by_weekday = (
        db.session.query(
            extract('dow', Paper.upload_date).label("weekday"),
            func.count(Paper.paper_id)
        )
        .group_by(extract('dow', Paper.upload_date))
        .order_by(extract('dow', Paper.upload_date))
        .all()
    )
    paper_weekday_map = {int(day): count for day, count in papers_by_weekday}

    return render_template(
        "stats.html",
        title="Analytics Dashboard",
        total_reviews=total_reviews,
        total_papers=total_papers,
        weekday_map=weekday_map,
        paper_weekday_map=paper_weekday_map
    )