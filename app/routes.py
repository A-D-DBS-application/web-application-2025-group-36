# app/routes.py
from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app, abort
from .models import db, User, Company, Paper, Review, PaperCompany, Complaint

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

    # ------------------------------
    # BEREKEN ACTIVE FILTERS 🎯
    # ------------------------------
    active_filters = 0
    if search:
        active_filters += 1
    if selected_domain != "all":
        active_filters += 1
    if selected_company:
        active_filters += 1
    if min_score:
        # Telt alleen als de waarde een geldig nummer is
        try:
            float(min_score)
            active_filters += 1
        except ValueError:
            pass 

    # ------------------------------
    # SCORE SUBQUERY
    # ------------------------------
    avg_subq = (
        db.session.query(
            Review.paper_id.label("paper_id"),
            func.avg(Review.score).label("avg_score"),
            func.count(Review.review_id).label("review_count")
        )
        .group_by(Review.paper_id)
        .subquery()
    )

    # ------------------------------
    # BASE QUERY (NO JOINEDLOAD YET!)
    # ------------------------------
    query = Paper.query.outerjoin(avg_subq, Paper.paper_id == avg_subq.c.paper_id)

    # ------------------------------
    # FILTER: SEARCH
    # ------------------------------
    if search:
        query = query.filter(
            or_(
                Paper.title.ilike(f"%{search}%"),
                Paper.abstract.ilike(f"%{search}%"),
                Paper.research_domain.ilike(f"%{search}%")
            )
        )

    # ------------------------------
    # FILTER: DOMAIN
    # ------------------------------
    if selected_domain != "all":
        query = query.filter(Paper.research_domain == selected_domain)

    # ------------------------------
    # FILTER: COMPANY (research facility)
    # ------------------------------
    if selected_company:
        query = (
            query.join(PaperCompany, PaperCompany.paper_id == Paper.paper_id)
                 .join(Company, Company.company_id == PaperCompany.company_id)
                 .filter(
                     PaperCompany.relation_type == "facility",
                     Company.name == selected_company
                 )
        )

    # ------------------------------
    # FILTER: MIN SCORE
    # ------------------------------
    if min_score:
        try:
            min_score_float = float(min_score)
            query = query.filter(func.coalesce(avg_subq.c.avg_score, 0) >= min_score_float)
        except:
            pass

    # ------------------------------
    # SORTING
    # ------------------------------
    if sort == "best":
        query = query.order_by(func.coalesce(avg_subq.c.avg_score, 0).desc())

    elif sort == "oldest":
        query = query.order_by(Paper.upload_date.asc())

    elif sort == "a_to_z":
        query = query.order_by(Paper.title.asc())

    elif sort == "z_to_a":
        query = query.order_by(Paper.title.desc())

    elif sort == "most_reviewed":
        query = query.order_by(func.coalesce(avg_subq.c.review_count, 0).desc())
    
    elif sort == "ai_score": 
        query = query.order_by((Paper.ai_business_score + Paper.ai_academic_score).desc())
    
    else:
        query = query.order_by(Paper.upload_date.desc())

    

    # ------------------------------
    # EXECUTE QUERY WITH JOINEDLOAD
    # --------------------------------
    papers = (
        query.options(
            joinedload(Paper.author),
            joinedload(Paper.reviews).joinedload(Review.reviewer),
            joinedload(Paper.reviews).joinedload(Review.company),
            joinedload(Paper.companies).joinedload(PaperCompany.company),
        )
        .all()
    )

    # ------------------------------
    # SCORE MAP
    # ------------------------------
    score_map = {
        row.paper_id: {
            "avg": round(float(row.avg_score), 1) if row.avg_score else None,
            "count": row.review_count,
        }
        for row in db.session.query(
            avg_subq.c.paper_id,
            avg_subq.c.avg_score,
            avg_subq.c.review_count
        ).all()
    }

    # ------------------------------
    # TOP 5 AI PAPERS
    # ------------------------------
    top5 = (
        Paper.query
        .filter(Paper.ai_status == "done")
        .order_by((Paper.ai_business_score + Paper.ai_academic_score).desc())
        .limit(5)
        .all()
    )

    # ------------------------------
    # INTERESTED LIST
    # ------------------------------
    interested_ids = set()
    if session.get("user_role") == "Company":
        user = User.query.get(session["user_id"])
        company = Company.query.filter_by(name=user.name).first()
        if company:
            links = PaperCompany.query.filter_by(
                company_id=company.company_id,
                relation_type="interest"
            ).all()
            interested_ids = {l.paper_id for l in links}

    # ------------------------------
    # FILTER POPULATION
    # ------------------------------
    domain_filters = sorted(d.research_domain for d in db.session.query(Paper.research_domain).distinct())
    companies = Company.query.order_by(Company.name).all()

    # ------------------------------
    # RENDER
    # ------------------------------
    return render_template(
        "dashboard.html",
        title="Dashboard",
        papers=papers,
        score_map=score_map,
        domains=domain_filters,
        companies=companies,
        selected_domain=selected_domain,
        selected_company=selected_company,
        min_score=min_score,
        sort=sort,
        query=search,
        interested_ids=interested_ids,
        top5=top5,
        # ⭐ CRUCIAAL: De variabele die we in HTML gebruiken
        active_filters=active_filters,
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
# DOWNLOAD PAPER
# ---------------------------------------------------
from flask import send_from_directory

@main.route("/paper/<int:paper_id>/download")
def download_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    # file_path = "papers/<filename>.pdf"
    rel_path = paper.file_path  
    filename = os.path.basename(rel_path)

    folder = current_app.config["UPLOAD_FOLDER"]  # static/papers

    return send_from_directory(
        folder,
        filename,
        as_attachment=True
    )

# ---------------------------------------------------
# UPLOAD PAPER – Researcher / Founder / Admin
# ---------------------------------------------------
@main.route("/upload_paper", methods=["GET", "POST"])
def upload_paper():
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    allowed_roles = ["Researcher", "Founder", "System/Admin"]
    if session.get("user_role") not in allowed_roles:
        return render_template("error_role.html", title="Access denied", required="Researcher")

    companies = Company.query.order_by(Company.name).all()
    domains = ["AI", "Robotics", "Biotech", "Software"]

    if request.method == "POST":

        # ---------------------------------------------
        # BASIC FIELDS
        # ---------------------------------------------
        title = request.form.get("title")
        abstract = request.form.get("abstract")
        research_domain = request.form.get("research_domain")
        custom_domain = request.form.get("custom_domain", "").strip()

        if research_domain == "Other" and custom_domain:
            research_domain = custom_domain

        if not title or not abstract:
            flash("Fill in all fields.", "error")
            return redirect(url_for("main.upload_paper"))

        # ---------------------------------------------
        # PDF UPLOAD
        # ---------------------------------------------
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Please upload a PDF file.", "error")
            return redirect(url_for("main.upload_paper"))

        if "." not in file.filename or not file.filename.lower().endswith(".pdf"):
            flash("PDF files only.", "error")
            return redirect(url_for("main.upload_paper"))

        filename = secure_filename(file.filename)
        unique_name = f"{session['user_id']}_{int(time.time())}_{filename}"

        # REAL filesystem path
        save_folder = current_app.config["UPLOAD_FOLDER"]
        abs_path = os.path.join(save_folder, unique_name)

        # Save file
        file.save(abs_path)

        # Relative path for HTML serving
        rel_path = f"papers/{unique_name}"

        # ---------------------------------------------
        # CREATE PAPER (AI pending)
        # ---------------------------------------------
        paper = Paper(
            title=title,
            abstract=abstract,
            research_domain=research_domain,
            user_id=session["user_id"],
            file_path=rel_path,
            ai_status="pending"
        )

        db.session.add(paper)
        db.session.flush()

        # ---------------------------------------------
        # LINK FACILITY
        # ---------------------------------------------
        selected_company_id = request.form.get("company_id")
        new_company_name = request.form.get("new_company", "").strip()
        new_company_industry = request.form.get("new_company_industry", "").strip()

        company_obj = None

        if new_company_name:
            company_obj = Company(name=new_company_name, industry=new_company_industry or None)
            db.session.add(company_obj)
            db.session.flush()
        elif selected_company_id:
            company_obj = Company.query.get(int(selected_company_id))

        if company_obj:
            db.session.add(PaperCompany(
                paper_id=paper.paper_id,
                company_id=company_obj.company_id,
                relation_type="facility"
            ))

        db.session.commit()

        # ---------------------------------------------
        # ⭐ AUTOMATIC AI ANALYSIS
        # ---------------------------------------------
        from pypdf import PdfReader
        from app.services.ai_analysis import analyze_paper_text

        print(f"🔍 Starting automatic AI analysis for: {abs_path}")

        try:
            reader = PdfReader(abs_path)
            full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

            ai_result = analyze_paper_text(full_text)

            if ai_result:
                paper.ai_business_score = ai_result.get("business_score")
                paper.ai_academic_score = ai_result.get("academic_score")
                paper.ai_summary = ai_result.get("summary")
                paper.ai_strengths = ai_result.get("strengths")
                paper.ai_weaknesses = ai_result.get("weaknesses")
                paper.ai_status = "done"
            else:
                paper.ai_status = "failed"

        except Exception as e:
            print("❌ AI Analysis FAILED:", e)
            paper.ai_status = "failed"

        db.session.commit()

        flash("Paper uploaded and analyzed automatically!", "success")
        return redirect(url_for("main.dashboard"))

    # GET — show form
    return render_template("upload_paper.html", companies=companies, domains=domains)




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
        joinedload(Paper.complaints),
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
    can_view_complaints = session.get("user_role") in ["System/Admin", "Founder"]
    complaints_sorted = []
    if can_view_complaints:
        complaints_sorted = sorted(
            paper.complaints,
            key=lambda c: c.created_at or datetime.min,
            reverse=True
        )
    complaint_submitted = request.args.get("complaint_submitted") == "1"

    return render_template(
        "paper_detail.html",
        title=paper.title,
        paper=paper,
        companies=companies,
        can_review=can_review,
        average_score=average_score,
        score_count=score_count,
        reviews_sorted=reviews_sorted,
        can_view_complaints=can_view_complaints,
        complaints=complaints_sorted,
        complaint_submitted=complaint_submitted,
    )


# ---------------------------------------------------
# REPORT / COMPLAINT
# ---------------------------------------------------
@main.route("/papers/<int:paper_id>/report", methods=["POST"])
def submit_complaint(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    description = (request.form.get("complaint_description") or "").strip()
    category = (request.form.get("complaint_category") or "Other").strip() or "Other"
    reporter_name = (request.form.get("reporter_name") or "").strip()
    reporter_email = (request.form.get("reporter_email") or "").strip()

    # Default fallbacks from session data
    if not reporter_name:
        reporter_name = session.get("user_name") or "Anonymous"

    if not description:
        flash("Please describe the issue before submitting a report.", "error")
        return redirect(url_for("main.paper_detail", paper_id=paper_id, _anchor="report-block"))

    complaint = Complaint(
        paper_id=paper.paper_id,
        reporter_name=reporter_name,
        reporter_email=reporter_email or None,
        category=category,
        description=description,
    )

    db.session.add(complaint)
    db.session.commit()

    flash("Thank you. Your report has been submitted for review.", "success")
    return redirect(
        url_for(
            "main.paper_detail",
            paper_id=paper.paper_id,
            complaint_submitted=1,
            _anchor="report-block"
        )
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

        # Maak de user aan
        user = User(name=name, email=email, role=role)
        db.session.add(user)
        db.session.flush()  # zodat user.user_id al bestaat

        # Als dit een company-account is: zorg dat er een Company bestaat met die naam
        if role == "Company":
            existing_company = Company.query.filter_by(name=name).first()
            if not existing_company:
                company = Company(name=name, industry=None)
                db.session.add(company)
                # geen flush/commit nodig hier, komt mee in dezelfde commit

        db.session.commit()

        session["user_id"] = user.user_id
        session["user_name"] = user.name
        session["user_role"] = user.role

        flash("Account created successfully.", "success")
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
    # ---------------------------
    # AUTH CHECKS
    # ---------------------------
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    paper = Paper.query.get_or_404(paper_id)

    if session.get("user_id") != paper.user_id and session.get("user_role") not in ["System/Admin", "Founder"]:
        flash("Access denied.", "error")
        return redirect(url_for("main.dashboard"))

    # ---------------------------
    # GET CURRENT FACILITY LINK
    # ---------------------------
    facility_link = PaperCompany.query.filter_by(
        paper_id=paper.paper_id,
        relation_type="facility"
    ).first()

    current_facility = None
    if facility_link:
        current_facility = Company.query.get(facility_link.company_id)

    # ---------------------------
    # POST: UPDATE PAPER
    # ---------------------------
    if request.method == "POST":
        # BASIC FIELDS
        paper.title = request.form.get("title", paper.title)
        paper.abstract = request.form.get("abstract", paper.abstract)

        # RESEARCH DOMAIN
        research_domain = request.form.get("research_domain") or paper.research_domain
        custom_domain = (request.form.get("custom_domain") or "").strip()

        # If "Other" was chosen
        if research_domain == "Other" and custom_domain:
            paper.research_domain = custom_domain
        else:
            paper.research_domain = research_domain

        # ---------------------------
        # FACILITY / COMPANY LOGIC
        # ---------------------------
        selected_company_id = request.form.get("company_id")
        new_company_name = (request.form.get("new_company") or "").strip()
        new_company_industry = (request.form.get("new_company_industry") or "").strip()

        company_obj = None

        # Create new company
        if new_company_name:
            company_obj = Company(
                name=new_company_name,
                industry=new_company_industry or None
            )
            db.session.add(company_obj)
            db.session.flush()  # ensures company_obj.company_id exists

        # Link existing company
        elif selected_company_id:
            company_obj = Company.query.get(int(selected_company_id))

        # Update PaperCompany relation
        if company_obj:
            PaperCompany.query.filter_by(
                paper_id=paper.paper_id,
                relation_type="facility"
            ).delete()

            db.session.add(PaperCompany(
                paper_id=paper.paper_id,
                company_id=company_obj.company_id,
                relation_type="facility"
            ))

        # SAVE
        db.session.commit()
        flash("Paper updated successfully.", "success")
        return redirect(url_for("main.dashboard"))

    # ---------------------------
    # GET: PREFILL PAGE
    # ---------------------------
    companies = Company.query.order_by(Company.name).all()
    domains = ["AI", "Robotics", "Biotech", "Health", "Energy", "Physics", "Chemistry"]  # or load dynamically

    return render_template(
        "update_paper.html",
        paper=paper,
        companies=companies,
        domains=domains,
        current_facility=current_facility,
        title="Update Paper",
        edit=True
    )

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
# ---------------------------------------------------
# Profile Page
# ---------------------------------------------------
@main.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("main.login"))

    user = User.query.get(user_id)

    authored_papers = (
        Paper.query
        .filter_by(user_id=user.user_id)
        .order_by(Paper.upload_date.desc())
        .all()
    )

    interested_papers = []
    company = None
    if user.role == "Company":
        company = Company.query.filter_by(name=user.name).first()
        if company:
            links = (
                PaperCompany.query
                .filter_by(company_id=company.company_id, relation_type="interest")
                .join(Paper, Paper.paper_id == PaperCompany.paper_id)
                .options(joinedload(PaperCompany.paper).joinedload(Paper.author))
                .all()
            )
            interested_papers = [link.paper for link in links]

    reviews = (
        Review.query
        .filter_by(reviewer_id=user.user_id)
        .order_by(Review.date_submitted.desc())
        .all()
    )

    papers_count = len(authored_papers)
    reviews_count = len(reviews)

    return render_template(
        "profile.html",
        user=user,
        company=company,
        authored_papers=authored_papers,
        interested_papers=interested_papers,
        reviews=reviews,
        papers_count=papers_count,
        reviews_count=reviews_count,
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
    # Total reviews
    total_reviews = Review.query.count()

    # Total papers
    total_papers = Paper.query.count()

    # Total AI analyses done
    ai_done = Paper.query.filter_by(ai_status="done").count()

    # Total AI analyses pending
    ai_pending = Paper.query.filter_by(ai_status="pending").count()

    # WEEKLY REVIEW HEATMAP
    weekday_map = {}
    reviews = Review.query.all()

    for r in reviews:
        if r.date_submitted:
            day = r.date_submitted.weekday()  # Monday=0, Sunday=6
            weekday_map[day] = weekday_map.get(day, 0) + 1

    # WEEKLY PAPER HEATMAP
    paper_weekday_map = {}
    papers = Paper.query.all()

    for p in papers:
        if p.upload_date:
            day = p.upload_date.weekday()
            paper_weekday_map[day] = paper_weekday_map.get(day, 0) + 1

    return render_template(
        "stats.html",
        total_reviews=total_reviews,
        total_papers=total_papers,
        weekday_map=weekday_map,
        paper_weekday_map=paper_weekday_map,
        ai_done=ai_done,
        ai_pending=ai_pending
    )

@main.route("/papers/<int:paper_id>/interest", methods=["POST"])
def toggle_interest(paper_id):
    # Enkel companies
    if not session.get("user_id") or session.get("user_role") != "Company":
        flash("Only company users can mark interest.", "error")
        return redirect(url_for("main.login"))

    user = User.query.get(session["user_id"])

    # simpele mapping: user.name == company.name
    company = Company.query.filter_by(name=user.name).first()
    if not company:
        flash("Your account is not linked to a company (no Company with this name found).", "error")
        return redirect(url_for("main.dashboard"))

    paper = Paper.query.get_or_404(paper_id)

    # bestaat er al een interest-link?
    interest_link = PaperCompany.query.filter_by(
        paper_id=paper.paper_id,
        company_id=company.company_id,
        relation_type="interest"
    ).first()

    if interest_link:
        # interesse weghalen
        db.session.delete(interest_link)
        flash("Paper removed from your company's interest list.", "success")
    else:
        # interesse toevoegen
        new_interest = PaperCompany(
            paper_id=paper.paper_id,
            company_id=company.company_id,
            relation_type="interest"
        )
        db.session.add(new_interest)
        flash("Paper marked as interesting for your company.", "success")

    db.session.commit()
    return redirect(request.referrer or url_for("main.dashboard"))

@main.route("/delete_account", methods=["POST"])
def delete_account():
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("main.index"))

    if user.role in ["System/Admin", "Founder"]:
        flash("Admin accounts cannot be deleted via the UI.", "error")
        return redirect(url_for("main.profile"))

    company = None
    if user.role == "Company":
        company = Company.query.filter_by(name=user.name).first()
        if company:
            
            PaperCompany.query.filter_by(company_id=company.company_id).delete()
            db.session.delete(company)

    db.session.delete(user)
    db.session.commit()

    session.clear()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("main.index"))


from app.services.pdf_extract import extract_text_from_pdf
from app.services.ai_analysis import analyze_paper_text
from app.config import BASE_DIR

# ---------------------------------------------------
# AI ANALYSIS ROUTE
# ---------------------------------------------------
@main.route("/analyze_paper/<int:paper_id>", methods=["POST"])
def analyze_paper(paper_id):

    paper = Paper.query.get_or_404(paper_id)

    # Build absolute file path for reading
    abs_path = os.path.abspath(
        os.path.join(current_app.root_path, "static", paper.file_path.replace("papers/", "papers/"))
    )

    # Debug print
    print("🔍 ABSOLUTE PDF PATH:", abs_path)

    if not os.path.exists(abs_path):
        flash("PDF not found on server.", "error")
        return redirect(url_for("main.paper_detail", paper_id=paper_id))

    # Extract PDF text
    try:
        from app.services.pdf_extract import extract_text_from_pdf
        full_text = extract_text_from_pdf(abs_path)
    except Exception as e:
        flash("PDF extraction failed.", "error")
        print("❌ PDF extraction error:", e)
        return redirect(url_for("main.paper_detail", paper_id=paper_id))

    # Run AI analysis
    from app.services.ai_analysis import analyze_paper_text

    analysis = analyze_paper_text(full_text)

    if analysis:
        paper.ai_business_score = analysis.get("business_score")
        paper.ai_academic_score = analysis.get("academic_score")
        paper.ai_summary = analysis.get("summary")
        paper.ai_strengths = analysis.get("strengths")
        paper.ai_weaknesses = analysis.get("weaknesses")
        paper.ai_status = "done"

        db.session.commit()
        flash("AI analysis completed.", "success")

    else:
        paper.ai_status = "failed"
        db.session.commit()
        flash("AI analysis failed.", "error")

    return redirect(url_for("main.paper_detail", paper_id=paper_id))
