# app/routes.py
from flask import (
    Blueprint,
    request,
    redirect,
    url_for,
    render_template,
    session,
    flash,
    current_app,
    abort,
    send_from_directory,
)
from functools import wraps
from collections import Counter
from datetime import datetime
import os
import time
import io # Nodig om bestanden in het geheugen te lezen
from supabase import create_client # Nodig voor communicatie met Supabase

from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from pypdf import PdfReader # Zorg dat je pypdf geinstalleerd hebt

from .models import db, User, Company, Paper, Review, PaperCompany, Complaint
# We gebruiken analyze_paper_text nog steeds, maar extract_text_from_pdf doen we nu inline
from app.services.ai_analysis import analyze_paper_text 

main = Blueprint("main", __name__)

# ---------------------------------------------------
# CONSTANTS & CONFIG
# ---------------------------------------------------
ALLOWED_EXTENSIONS = {"pdf"}
BUCKET_NAME = "paper-pdfs" # Zorg dat deze bucket bestaat in Supabase en 'Public' is

def get_supabase():
    """Helper om de Supabase client op te halen uit de config"""
    url = current_app.config["SUPABASE_URL"]
    key = current_app.config["SUPABASE_KEY"]
    return create_client(url, key)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(view):
    """Decorator: require a logged-in user."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)
    return wrapped_view

def roles_required(*allowed_roles):
    """Decorator: require user to have one of the given roles."""
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in first.", "error")
                return redirect(url_for("main.login"))

            if session.get("user_role") not in allowed_roles:
                flash("Access denied.", "error")
                return redirect(url_for("main.index"))

            return view(*args, **kwargs)
        return wrapped_view
    return decorator

# ---------------------------------------------------
# BASIC PAGES
# ---------------------------------------------------
@main.route("/")
def index():
    try:
        total_papers = Paper.query.count()
    except:
        total_papers = 0

    try:
        total_companies = Company.query.count()
    except:
        total_companies = 0

    return render_template(
        "home.html", 
        title="Home",
        total_papers=total_papers,
        total_companies=total_companies 
    )

@main.route("/vision")
def vision():
    return render_template("vision.html", title="Vision")

@main.route("/about")
def about():
    return render_template("about.html", title="About")


# ---------------------------------------------------
# DASHBOARD HELPERS
# ---------------------------------------------------
def get_user_domain_preferences(user: User):
    """Return normalized preference scores per domain for this user."""
    counts = Counter()
    total = 0

    for review in user.reviews:
        if review.paper and review.paper.research_domain:
            counts[review.paper.research_domain] += 1
            total += 1

    if total == 0:
        return {} 

    return {domain: count / total for domain, count in counts.items()}


def compute_paper_score(paper: Paper, user_prefs, score_map, now: datetime):
    """Combine personalization, popularity, and recency into one score."""
    domain = paper.research_domain
    pref_score = user_prefs.get(domain, 0)

    pop_score = 0
    if paper.paper_id in score_map and score_map[paper.paper_id]["avg"] is not None:
        pop_score = score_map[paper.paper_id]["avg"] / 5.0

    days_old = (now - paper.upload_date).days if paper.upload_date else 365
    recency_score = max(0, 1 - (days_old / 30))

    return 0.5 * pref_score + 0.3 * pop_score + 0.2 * recency_score


def get_dashboard_data(args, sess):
    """Shared dashboard logic: filters, sorting, scores & context."""
    search = args.get("q", "").strip()
    selected_domain = args.get("domain", "all")
    selected_company = args.get("company", "").strip()
    min_score = args.get("min_score", "").strip()
    sort = args.get("sort", "newest")

    # ------------------------------
    # ACTIVE FILTERS
    # ------------------------------
    active_filters = 0
    if search: active_filters += 1
    if selected_domain != "all": active_filters += 1
    if selected_company: active_filters += 1
    if min_score:
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
            func.count(Review.review_id).label("review_count"),
        )
        .group_by(Review.paper_id)
        .subquery()
    )

    # ------------------------------
    # BASE QUERY
    # ------------------------------
    query = Paper.query.outerjoin(avg_subq, Paper.paper_id == avg_subq.c.paper_id)

    # SEARCH
    if search:
        query = query.filter(
            or_(
                Paper.title.ilike(f"%{search}%"),
                Paper.abstract.ilike(f"%{search}%"),
                Paper.research_domain.ilike(f"%{search}%"),
            )
        )

    # DOMAIN
    if selected_domain != "all":
        query = query.filter(Paper.research_domain == selected_domain)

    # COMPANY (facility)
    if selected_company:
        query = (
            query.join(PaperCompany, PaperCompany.paper_id == Paper.paper_id)
            .join(Company, Company.company_id == PaperCompany.company_id)
            .filter(
                PaperCompany.relation_type == "facility",
                Company.name == selected_company,
            )
        )

    # MIN SCORE
    if min_score:
        try:
            min_score_float = float(min_score)
            query = query.filter(
                func.coalesce(avg_subq.c.avg_score, 0) >= min_score_float
            )
        except ValueError:
            pass

    # SORTING
    if sort == "best":
        query = query.order_by(func.coalesce(avg_subq.c.avg_score, 0).desc())
    elif sort == "oldest":
        query = query.order_by(Paper.upload_date.asc())
    elif sort == "a_to_z":
        query = query.order_by(Paper.title.asc())
    elif sort == "z_to_a":
        query = query.order_by(Paper.title.desc())
    elif sort == "most_reviewed":
        query = query.order_by(
            func.coalesce(avg_subq.c.review_count, 0).desc()
        )
    elif sort == "ai_score":
        query = query.order_by(
            (Paper.ai_business_score + Paper.ai_academic_score).desc()
        )
    else:
        # newest
        query = query.order_by(Paper.upload_date.desc())

    # EXECUTE WITH JOINEDLOAD
    papers = (
        query.options(
            joinedload(Paper.author),
            joinedload(Paper.reviews).joinedload(Review.reviewer),
            joinedload(Paper.reviews).joinedload(Review.company),
            joinedload(Paper.companies).joinedload(PaperCompany.company),
        ).all()
    )

    # SCORE MAP
    score_map = {
        row.paper_id: {
            "avg": round(float(row.avg_score), 1) if row.avg_score else None,
            "count": row.review_count,
        }
        for row in db.session.query(
            avg_subq.c.paper_id,
            avg_subq.c.avg_score,
            avg_subq.c.review_count,
        ).all()
    }

    # TOP 5 AI PAPERS
    top5 = (
        Paper.query.filter(Paper.ai_status == "done")
        .order_by((Paper.ai_business_score + Paper.ai_academic_score).desc())
        .limit(5)
        .all()
    )

    # INTERESTED LIST
    interested_ids = set()
    if sess.get("user_role") == "Company":
        user = User.query.get(sess["user_id"])
        company = Company.query.filter_by(name=user.name).first()
        if company:
            links = PaperCompany.query.filter_by(
                company_id=company.company_id, relation_type="interest"
            ).all()
            interested_ids = {l.paper_id for l in links}

    # FILTER POPULATION
    domain_filters = sorted(
        d[0] for d in db.session.query(Paper.research_domain).distinct()
    )
    companies = Company.query.order_by(Company.name).all()

    return {
        "title": "Dashboard",
        "papers": papers,
        "score_map": score_map,
        "domains": domain_filters,
        "companies": companies,
        "selected_domain": selected_domain,
        "selected_company": selected_company,
        "min_score": min_score,
        "sort": sort,
        "query": search,
        "interested_ids": interested_ids,
        "top5": top5,
        "active_filters": active_filters,
    }


# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------
@main.route("/dashboard")
def dashboard():
    context = get_dashboard_data(request.args, session)
    return render_template("dashboard.html", **context)


@main.route("/search_papers")
def search_papers():
    incoming = request.args.get("q", "").strip()
    return redirect(url_for("main.dashboard", q=incoming))


# ---------------------------------------------------
# DOWNLOAD PAPER (AANGEPAST VOOR SUPABASE)
# ---------------------------------------------------
@main.route("/paper/<int:paper_id>/download")
def download_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    
    # We bouwen de publieke URL naar Supabase
    supabase_url = current_app.config["SUPABASE_URL"]
    
    # URL Formaat: https://[PROJECT_ID].supabase.co/storage/v1/object/public/[BUCKET]/[PATH]
    # Let op: 'paper.file_path' is nu alleen de unieke bestandsnaam (bijv. "12_178383_thesis.pdf")
    public_url = f"{supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{paper.file_path}"
    
    # We redirecten de gebruiker naar Supabase, waar de browser de PDF zal openen/downloaden
    return redirect(public_url)


# ---------------------------------------------------
# UPLOAD PAPER HELPERS (AANGEPAST VOOR SUPABASE)
# ---------------------------------------------------
def get_upload_paper_context():
    companies = Company.query.order_by(Company.name).all()
    domains = ["AI", "Robotics", "Biotech", "Software"]
    return {"companies": companies, "domains": domains, "title": "Upload Paper"}


def process_paper_upload(user_id: int):
    """Shared POST-logic voor upload_paper route."""
    title = request.form.get("title")
    abstract = request.form.get("abstract")
    research_domain = request.form.get("research_domain")
    custom_domain = (request.form.get("custom_domain") or "").strip()

    if research_domain == "Other" and custom_domain:
        research_domain = custom_domain

    if not title or not abstract:
        flash("Fill in all fields.", "error")
        return redirect(url_for("main.upload_paper"))

    # PDF upload
    file = request.files.get("file")

    if not file or file.filename == "":
        flash("Please upload a PDF file.", "error")
        return redirect(url_for("main.upload_paper"))

    if not allowed_file(file.filename):
        flash("PDF files only.", "error")
        return redirect(url_for("main.upload_paper"))

    # 1. Bestandsnaam veilig maken
    filename = secure_filename(file.filename)
    unique_name = f"{user_id}_{int(time.time())}_{filename}" # Dit wordt de key in Supabase

    # 2. Uploaden naar Supabase Storage
    try:
        supabase = get_supabase()
        
        # We moeten de file pointer uitlezen. 
        # BELANGRIJK: Na .read() staat de pointer aan het eind. We slaan het op in een variabele.
        file_content = file.read() 
        
        res = supabase.storage.from_(BUCKET_NAME).upload(
            path=unique_name,
            file=file_content,
            file_options={"content-type": "application/pdf"}
        )
        
        # Opslaan in database: Alleen de bestandsnaam (path in bucket)
        db_file_path = unique_name
        
    except Exception as e:
        print(f"❌ SUPABASE UPLOAD ERROR: {e}")
        flash(f"Upload failed: {e}", "error")
        return redirect(url_for("main.upload_paper"))

    # CREATE PAPER
    paper = Paper(
        title=title,
        abstract=abstract,
        research_domain=research_domain,
        user_id=user_id,
        file_path=db_file_path, # Nu de Supabase filename
        ai_status="pending",
    )

    db.session.add(paper)
    db.session.flush()

    # LINK FACILITY
    selected_company_id = request.form.get("company_id")
    new_company_name = (request.form.get("new_company") or "").strip()
    new_company_industry = (request.form.get("new_company_industry") or "").strip()

    company_obj = None

    if new_company_name:
        company_obj = Company(
            name=new_company_name, industry=new_company_industry or None
        )
        db.session.add(company_obj)
        db.session.flush()
    elif selected_company_id:
        company_obj = Company.query.get(int(selected_company_id))

    if company_obj:
        db.session.add(
            PaperCompany(
                paper_id=paper.paper_id,
                company_id=company_obj.company_id,
                relation_type="facility",
            )
        )

    db.session.commit()

    # AUTOMATIC AI ANALYSIS (Aangepast voor In-Memory PDF)
    print(f"🔍 Starting automatic AI analysis for: {unique_name}")

    try:
        # We gebruiken de bytes die we net hebben geupload (file_content)
        # We wrappen dit in io.BytesIO zodat PyPDF denkt dat het een bestand is
        pdf_stream = io.BytesIO(file_content)
        
        reader = PdfReader(pdf_stream)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        # Roep de AI service aan
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


# ---------------------------------------------------
# UPLOAD PAPER – Researcher / Founder / Admin
# ---------------------------------------------------
@main.route("/upload_paper", methods=["GET", "POST"])
@login_required
@roles_required("Researcher", "Founder", "System/Admin")
def upload_paper():
    if request.method == "POST":
        return process_paper_upload(session["user_id"])

    context = get_upload_paper_context()
    return render_template("upload_paper.html", **context)


# ---------------------------------------------------
# PAPER DETAIL + REVIEWS HELPERS
# ---------------------------------------------------
def load_paper_with_relations(paper_id: int) -> Paper:
    return (
        Paper.query.options(
            joinedload(Paper.author),
            joinedload(Paper.reviews).joinedload(Review.reviewer),
            joinedload(Paper.reviews).joinedload(Review.company),
            joinedload(Paper.companies).joinedload(PaperCompany.company),
            joinedload(Paper.complaints),
        ).get_or_404(paper_id)
    )


def handle_review_post(paper: Paper, can_review: bool):
    if not session.get("user_id"):
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    if not can_review:
        flash(
            "Only reviewers or company users can leave a score/comment.",
            "error",
        )
        return redirect(url_for("main.paper_detail", paper_id=paper.paper_id))

    score_raw = request.form.get("score")
    comments = (request.form.get("comments") or "").strip()
    company_id = request.form.get("company_id")

    if not score_raw and not comments:
        flash("Add at least a score or a comment.", "error")
        return redirect(url_for("main.paper_detail", paper_id=paper.paper_id))

    score_value = None
    if score_raw:
        try:
            score_value = float(score_raw)
        except ValueError:
            flash("Score must be a number between 0 and 10.", "error")
            return redirect(url_for("main.paper_detail", paper_id=paper.paper_id))
        if score_value < 0 or score_value > 10:
            flash("Score must be between 0 and 10.", "error")
            return redirect(url_for("main.paper_detail", paper_id=paper.paper_id))

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


def build_paper_detail_context(
    paper: Paper, companies, can_review: bool, complaint_submitted: bool
):
    scored = [r.score for r in paper.reviews if r.score is not None]
    average_score = round(sum(scored) / len(scored), 1) if scored else None
    score_count = len(scored)
    reviews_sorted = sorted(
        paper.reviews, key=lambda r: r.date_submitted, reverse=True
    )

    can_view_complaints = session.get("user_role") in ["System/Admin", "Founder"]
    complaints_sorted = []
    if can_view_complaints:
        complaints_sorted = sorted(
            paper.complaints,
            key=lambda c: c.created_at or datetime.min,
            reverse=True,
        )

    return {
        "title": paper.title,
        "paper": paper,
        "companies": companies,
        "can_review": can_review,
        "average_score": average_score,
        "score_count": score_count,
        "reviews_sorted": reviews_sorted,
        "can_view_complaints": can_view_complaints,
        "complaints": complaints_sorted,
        "complaint_submitted": complaint_submitted,
    }


# ---------------------------------------------------
# PAPER DETAIL + REVIEWS
# ---------------------------------------------------
@main.route("/papers/<int:paper_id>", methods=["GET", "POST"])
def paper_detail(paper_id):
    paper = load_paper_with_relations(paper_id)
    companies = Company.query.order_by(Company.name).all()
    can_review_roles = ["Reviewer", "Company", "System/Admin", "Founder"]
    can_review = session.get("user_role") in can_review_roles

    if request.method == "POST":
        return handle_review_post(paper, can_review)

    complaint_submitted = request.args.get("complaint_submitted") == "1"
    context = build_paper_detail_context(
        paper, companies, can_review, complaint_submitted
    )
    return render_template("paper_detail.html", **context)


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

    if not reporter_name:
        reporter_name = session.get("user_name") or "Anonymous"

    if not description:
        flash("Please describe the issue before submitting a report.", "error")
        return redirect(
            url_for(
                "main.paper_detail", paper_id=paper_id, _anchor="report-block"
            )
        )

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
            _anchor="report-block",
        )
    )


# ---------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------
@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))


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
        db.session.flush()  # zodat user.user_id al bestaat

        if role == "Company":
            existing_company = Company.query.filter_by(name=name).first()
            if not existing_company:
                company = Company(name=name, industry=None)
                db.session.add(company)

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
@login_required
def change_role():
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
    return render_template(
        "change_role.html", title="Change Role", roles=roles, user=user
    )


# ---------------------------------------------------
# UPDATE PAPER HELPERS
# ---------------------------------------------------
def build_update_paper_context(paper: Paper, current_facility):
    companies = Company.query.order_by(Company.name).all()
    domains = [
        "AI",
        "Robotics",
        "Biotech",
        "Health",
        "Energy",
        "Physics",
        "Chemistry",
    ]
    return {
        "paper": paper,
        "companies": companies,
        "domains": domains,
        "current_facility": current_facility,
        "title": "Update Paper",
        "edit": True,
    }


def handle_update_paper_post(paper: Paper):
    # BASIC FIELDS
    paper.title = request.form.get("title", paper.title)
    paper.abstract = request.form.get("abstract", paper.abstract)

    # RESEARCH DOMAIN
    research_domain = request.form.get("research_domain") or paper.research_domain
    custom_domain = (request.form.get("custom_domain") or "").strip()

    if research_domain == "Other" and custom_domain:
        paper.research_domain = custom_domain
    else:
        paper.research_domain = research_domain

    # FACILITY / COMPANY LOGIC
    selected_company_id = request.form.get("company_id")
    new_company_name = (request.form.get("new_company") or "").strip()
    new_company_industry = (request.form.get("new_company_industry") or "").strip()

    company_obj = None

    if new_company_name:
        company_obj = Company(
            name=new_company_name,
            industry=new_company_industry or None,
        )
        db.session.add(company_obj)
        db.session.flush()
    elif selected_company_id:
        company_obj = Company.query.get(int(selected_company_id))

    if company_obj:
        PaperCompany.query.filter_by(
            paper_id=paper.paper_id,
            relation_type="facility",
        ).delete()

        db.session.add(
            PaperCompany(
                paper_id=paper.paper_id,
                company_id=company_obj.company_id,
                relation_type="facility",
            )
        )

    db.session.commit()
    flash("Paper updated successfully.", "success")
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------
# UPDATE PAPER
# ---------------------------------------------------
@main.route("/update_paper/<int:paper_id>", methods=["GET", "POST"])
@login_required
def update_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    if session.get("user_id") != paper.user_id and session.get("user_role") not in [
        "System/Admin",
        "Founder",
    ]:
        flash("Access denied.", "error")
        return redirect(url_for("main.dashboard"))

    facility_link = PaperCompany.query.filter_by(
        paper_id=paper.paper_id, relation_type="facility"
    ).first()

    current_facility = (
        Company.query.get(facility_link.company_id) if facility_link else None
    )

    if request.method == "POST":
        return handle_update_paper_post(paper)

    context = build_update_paper_context(paper, current_facility)
    return render_template("update_paper.html", **context)


# ---------------------------------------------------
# DELETE PAPER
# ---------------------------------------------------
# app/routes.py - Zoek de bestaande delete_paper functie en vervang hem hiermee:

@main.route("/paper/<int:paper_id>/delete", methods=["POST"])
@login_required
def delete_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    
    # Check permissies (zoals voorheen)
    if session.get("user_id") != paper.user_id and session.get("user_role") not in [
        "System/Admin",
        "Founder",
    ]:
        abort(403)

    # ---------------------------------------------------------
    # STAP 1: Verwijder het bestand uit Supabase Storage
    # ---------------------------------------------------------
    try:
        supabase = get_supabase()
        # De .remove() functie verwacht een LIJST van bestandsnamen
        # Let op: paper.file_path is nu de naam in de bucket (bijv. "12_1783_thesis.pdf")
        res = supabase.storage.from_(BUCKET_NAME).remove([paper.file_path])
        
        # Optioneel: check of er een error was in de response (afhankelijk van versie)
        # print("Supabase remove result:", res)

    except Exception as e:
        # Als het mislukt (bijv. bestand bestond al niet meer), loggen we het
        # Maar we gaan wel door met de DB delete, anders kan de gebruiker nooit van zijn paper af.
        print(f"⚠️ LET OP: Kon bestand niet uit Supabase verwijderen: {e}")

    # ---------------------------------------------------------
    # STAP 2: Verwijder de record uit de Database
    # ---------------------------------------------------------
    db.session.delete(paper)
    db.session.commit()
    
    flash("Paper deleted successfully (and removed from cloud storage).", "success")
    return redirect(url_for("main.dashboard"))

# ---------------------------------------------------
# ADD COMPANY
# ---------------------------------------------------
@main.route("/add_company", methods=["GET", "POST"])
@login_required
@roles_required("System/Admin", "Founder")
def add_company():
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
# PROFILE HELPERS
# ---------------------------------------------------
def get_profile_data(user_id: int):
    user = User.query.get(user_id)

    authored_papers = (
        Paper.query.filter_by(user_id=user.user_id)
        .order_by(Paper.upload_date.desc())
        .all()
    )

    interested_papers = []
    company = None
    recommended_papers = []

    if user.role == "Company":
        company = Company.query.filter_by(name=user.name).first()
        if company:
            links = (
                PaperCompany.query.filter_by(
                    company_id=company.company_id, relation_type="interest"
                )
                .join(Paper, Paper.paper_id == PaperCompany.paper_id)
                .options(joinedload(PaperCompany.paper).joinedload(Paper.author))
                .all()
            )
            interested_papers = [link.paper for link in links]

            if company.interests:
                tags = [t.strip() for t in company.interests.split(",") if t.strip()]
                if tags:
                    recommended_papers = (
                        Paper.query.filter(Paper.research_domain.in_(tags))
                        .order_by(Paper.upload_date.desc())
                        .limit(5)
                        .all()
                    )

    reviews = (
        Review.query.filter_by(reviewer_id=user.user_id)
        .order_by(Review.date_submitted.desc())
        .all()
    )

    papers_count = len(authored_papers)
    reviews_count = len(reviews)

    return {
        "user": user,
        "company": company,
        "authored_papers": authored_papers,
        "interested_papers": interested_papers,
        "reviews": reviews,
        "papers_count": papers_count,
        "reviews_count": reviews_count,
        "recommended_papers": recommended_papers,
    }


# ---------------------------------------------------
# PROFILE
# ---------------------------------------------------
@main.route("/profile")
@login_required
def profile():
    context = get_profile_data(session["user_id"])
    return render_template("profile.html", **context)


# ---------------------------------------------------
# EDIT PROFILE HELPERS
# ---------------------------------------------------
INTEREST_TAGS = [
    "AI",
    "Robotics",
    "Biotech",
    "Health",
    "Energy",
    "Software",
    "Sustainability",
]


def build_edit_profile_context(user: User):
    company = None
    company_interests_list = []

    if user.role == "Company":
        company = Company.query.filter_by(name=user.name).first()
        if company and company.interests:
            company_interests_list = [
                t.strip() for t in company.interests.split(",") if t.strip()
            ]

    return {
        "user": user,
        "company": company,
        "company_interests": company_interests_list,
        "interest_tags": INTEREST_TAGS,
        "title": "Edit Profile",
    }


def handle_edit_profile_post(user: User):
    company = None
    if user.role == "Company":
        company = Company.query.filter_by(name=user.name).first()

    new_name = (request.form.get("name") or "").strip()
    new_email = (request.form.get("email") or "").strip()

    user.name = new_name or user.name
    user.email = new_email or user.email

    if user.role == "Company" and company:
        selected_interests = request.form.getlist("interests")
        company.interests = ",".join(selected_interests) if selected_interests else None

    db.session.commit()

    session["user_name"] = user.name
    session["user_email"] = user.email

    flash("Profile updated successfully!", "success")
    return redirect(url_for("main.profile"))


# ---------------------------------------------------
# EDIT PROFILE
# ---------------------------------------------------
@main.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    user = User.query.get(session["user_id"])

    if request.method == "POST":
        return handle_edit_profile_post(user)

    context = build_edit_profile_context(user)
    return render_template("edit_profile.html", **context)


# ---------------------------------------------------
# STATS HELPERS
# ---------------------------------------------------
def get_stats_data():
    total_reviews = Review.query.count()
    total_papers = Paper.query.count()
    ai_done = Paper.query.filter_by(ai_status="done").count()
    ai_pending = Paper.query.filter_by(ai_status="pending").count()

    weekday_map = {}
    for r in Review.query.all():
        if r.date_submitted:
            day = r.date_submitted.weekday()
            weekday_map[day] = weekday_map.get(day, 0) + 1

    paper_weekday_map = {}
    for p in Paper.query.all():
        if p.upload_date:
            day = p.upload_date.weekday()
            paper_weekday_map[day] = paper_weekday_map.get(day, 0) + 1

    return {
        "total_reviews": total_reviews,
        "total_papers": total_papers,
        "weekday_map": weekday_map,
        "paper_weekday_map": paper_weekday_map,
        "ai_done": ai_done,
        "ai_pending": ai_pending,
    }


# ---------------------------------------------------
# STATS
# ---------------------------------------------------
@main.route("/stats")
def stats():
    context = get_stats_data()
    return render_template("stats.html", **context)


# ---------------------------------------------------
# INTEREST TOGGLE
# ---------------------------------------------------
@main.route("/papers/<int:paper_id>/interest", methods=["POST"])
@login_required
def toggle_interest(paper_id):
    if session.get("user_role") != "Company":
        flash("Only company users can mark interest.", "error")
        return redirect(url_for("main.login"))

    user = User.query.get(session["user_id"])

    company = Company.query.filter_by(name=user.name).first()
    if not company:
        flash(
            "Your account is not linked to a company (no Company with this name found).",
            "error",
        )
        return redirect(url_for("main.dashboard"))

    paper = Paper.query.get_or_404(paper_id)

    interest_link = PaperCompany.query.filter_by(
        paper_id=paper.paper_id,
        company_id=company.company_id,
        relation_type="interest",
    ).first()

    if interest_link:
        db.session.delete(interest_link)
        flash("Paper removed from your company's interest list.", "success")
    else:
        new_interest = PaperCompany(
            paper_id=paper.paper_id,
            company_id=company.company_id,
            relation_type="interest",
        )
        db.session.add(new_interest)
        flash("Paper marked as interesting for your company.", "success")

    db.session.commit()
    return redirect(request.referrer or url_for("main.dashboard"))


# ---------------------------------------------------
# DELETE ACCOUNT
# ---------------------------------------------------
@main.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("main.index"))

    if user.role in ["System/Admin", "Founder"]:
        flash("Admin accounts cannot be deleted via the UI.", "error")
        return redirect(url_for("main.profile"))

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


# ---------------------------------------------------
# AI ANALYSIS ROUTE (AANGEPAST VOOR SUPABASE)
# ---------------------------------------------------
@main.route("/analyze_paper/<int:paper_id>", methods=["POST"])
@login_required
def analyze_paper(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    # In de nieuwe situatie hebben we geen lokaal path meer.
    # We moeten het bestand downloaden van Supabase om het opnieuw te analyseren.
    print(f"🔍 Re-analyzing Supabase file: {paper.file_path}")

    try:
        supabase = get_supabase()
        
        # Download bytes van Supabase
        res = supabase.storage.from_(BUCKET_NAME).download(paper.file_path)
        
        # Zet bytes om naar stream
        pdf_stream = io.BytesIO(res)
        
        # Lees PDF
        reader = PdfReader(pdf_stream)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        
    except Exception as e:
        flash("PDF extraction from Supabase failed.", "error")
        print("❌ PDF extraction error:", e)
        return redirect(url_for("main.paper_detail", paper_id=paper_id))

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
# ---------------------------------------------------
# END OF FILE