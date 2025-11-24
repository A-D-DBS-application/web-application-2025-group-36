# app/routes.py
from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app, abort
from .models import db, User, Company, Paper, Review, PaperCompany

from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
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
# DASHBOARD / ARCHIEF
# ---------------------------------------------------
@main.route("/dashboard")
def dashboard():
    ensure_demo_content()

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

    domain_rows = db.session.query(Paper.research_domain).distinct().all()
    domain_filters = sorted({d.research_domain for d in domain_rows if d.research_domain}.union(set(POPULAR_DOMAINS)))
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


@main.route("/search_papers")
def search_papers():
    # Old endpoint now routes to the new dashboard, preserving search queries.
    incoming = request.args.get("q", "").strip()
    return redirect(url_for("main.dashboard", q=incoming))


# ---------------------------------------------------
# HELPERS FUNCTION (UPLOAD PAPERS)
# ---------------------------------------------------
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------
# DEMO SEEDING FOR DASHBOARD
# ---------------------------------------------------
DEMO_PAPERS = [
    {
        "title": "Learning Dexterous In-Hand Manipulation",
        "abstract": "OpenAI's robotics team demonstrates how deep reinforcement learning can master in-hand object reorientation on a Shadow Dexterous Hand, with sim-to-real transfer and domain randomization.",
        "file_path": "https://arxiv.org/pdf/1808.00177.pdf",
        "research_domain": "Robotics",
        "company": "Atlas Robotics"
    },
    {
        "title": "GraphDTA: prediction of drug-target binding affinity using graph convolutional networks",
        "abstract": "GraphDTA replaces molecular fingerprints with graph neural networks to predict binding affinity, improving biotech screening pipelines with end-to-end learned representations.",
        "file_path": "https://arxiv.org/pdf/1912.07047.pdf",
        "research_domain": "Biotech",
        "company": "BioNexus Labs"
    },
]

DEMO_COMPANIES = [
    {"name": "Atlas Robotics", "industry": "Autonomous systems"},
    {"name": "BioNexus Labs", "industry": "Biotech & drug discovery"},
    {"name": "Aether Insight", "industry": "AI research collective"},
]

def ensure_demo_content():
    """Populate the database with two high-quality demo papers and sample reviews."""
    created = False

    demo_researcher = User.query.filter_by(email="demo.researcher@reviewr.ai").first()
    if not demo_researcher:
        demo_researcher = User(
            name="Demo Researcher",
            email="demo.researcher@reviewr.ai",
            role="Researcher"
        )
        db.session.add(demo_researcher)
        created = True

    demo_reviewer = User.query.filter_by(email="demo.reviewer@reviewr.ai").first()
    if not demo_reviewer:
        demo_reviewer = User(
            name="Guest Reviewer",
            email="demo.reviewer@reviewr.ai",
            role="Reviewer"
        )
        db.session.add(demo_reviewer)
        created = True

    demo_founder = User.query.filter_by(email="demo.founder@reviewr.ai").first()
    if not demo_founder:
        demo_founder = User(
            name="Venture Partner",
            email="demo.founder@reviewr.ai",
            role="Founder"
        )
        db.session.add(demo_founder)
        created = True

    company_map = {}
    for entry in DEMO_COMPANIES:
        company = Company.query.filter_by(name=entry["name"]).first()
        if not company:
            company = Company(name=entry["name"], industry=entry["industry"])
            db.session.add(company)
            created = True
        company_map[entry["name"]] = company

    db.session.flush()

    for paper_data in DEMO_PAPERS:
        paper = Paper.query.filter_by(title=paper_data["title"]).first()
        if not paper:
            paper = Paper(
                title=paper_data["title"],
                abstract=paper_data["abstract"],
                research_domain=paper_data["research_domain"],
                user_id=demo_researcher.user_id,
                file_path=paper_data["file_path"],
            )
            db.session.add(paper)
            created = True
        else:
            # keep demo content fresh if already exists
            paper.abstract = paper_data["abstract"]
            paper.research_domain = paper_data["research_domain"]
            paper.file_path = paper_data["file_path"]

        db.session.flush()

        company = company_map.get(paper_data["company"])
        if company and not PaperCompany.query.filter_by(
            paper_id=paper.paper_id, company_id=company.company_id
        ).first():
            db.session.add(PaperCompany(paper_id=paper.paper_id, company_id=company.company_id))
            created = True

    sample_reviews = [
        {
            "paper_title": DEMO_PAPERS[0]["title"],
            "score": 9.1,
            "comments": "Sterk stuk: robuuste sim-to-real pipeline en duidelijke metrics. Zou meteen een POC willen draaien in onze productielijn.",
            "reviewer": demo_reviewer,
            "company": company_map["Atlas Robotics"],
        },
        {
            "paper_title": DEMO_PAPERS[1]["title"],
            "score": 8.7,
            "comments": "Veelbelovende biotech stack; graph representaties geven betere precisie. Interesse in samenwerking voor FTI screening.",
            "reviewer": demo_founder,
            "company": company_map["BioNexus Labs"],
        },
    ]

    for review_data in sample_reviews:
        paper = Paper.query.filter_by(title=review_data["paper_title"]).first()
        if not paper:
            continue

        exists = Review.query.filter_by(
            paper_id=paper.paper_id,
            reviewer_id=review_data["reviewer"].user_id,
            company_id=review_data["company"].company_id,
        ).first()

        if not exists:
            review = Review(
                paper_id=paper.paper_id,
                reviewer_id=review_data["reviewer"].user_id,
                company_id=review_data["company"].company_id,
                score=review_data["score"],
                comments=review_data["comments"],
            )
            db.session.add(review)
            created = True

    if created:
        db.session.commit()

POPULAR_DOMAINS = ["AI", "Robotics", "Biotech", "Climate", "Security", "Data & Analytics"]
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
            research_domain=research_domain,
            user_id=session.get("user_id"),
            file_path=relative_path
        )
        db.session.add(paper)
        db.session.flush()

        # Koppel aan een bestaande of nieuwe company
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

    # GET: formulier tonen
    return render_template("upload_paper.html", title="Upload Paper", domains=POPULAR_DOMAINS, companies=companies)


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
    roles = ["Researcher", "Reviewer", "Company", "User", "System/Admin", "Founder"]

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
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        title = request.form.get("title")
        abstract = request.form.get("abstract")
        research_domain = request.form.get("research_domain") or paper.research_domain
        custom_domain = (request.form.get("custom_domain") or "").strip()
        selected_company_id = request.form.get("company_id")
        new_company_name = (request.form.get("new_company") or "").strip()
        new_company_industry = (request.form.get("new_company_industry") or "").strip()

        if not title or not abstract:
            flash("Fill in title and abstract.", "error")
            return redirect(url_for("main.update_paper", paper_id=paper_id))

        if research_domain == "Other" and custom_domain:
            research_domain = custom_domain

        # Update database
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

    # GET: formulier tonen met bestaande data
    companies = Company.query.order_by(Company.name).all()
    return render_template("update_paper.html", paper=paper, title="Update Paper", domains=POPULAR_DOMAINS, companies=companies)
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
    return redirect(url_for("main.dashboard"))


# ---------------------------------------------------
# PAPER DETAIL + REVIEWS
# ---------------------------------------------------
@main.route("/papers/<int:paper_id>", methods=["GET", "POST"])
def paper_detail(paper_id):
    ensure_demo_content()

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
# ADD COMPANY
# ---------------------------------------------------
@main.route("/add_company", methods=["GET", "POST"])
def add_company():
    # Controleer of ingelogd en rol
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
