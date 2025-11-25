# app/routes.py
from flask import Blueprint, request, redirect, url_for, render_template, session, flash, current_app, abort
from .models import db, User, Company, Paper, Review, PaperCompany

from types import SimpleNamespace
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
    search = request.args.get("q", "").strip()
    selected_domain = request.args.get("domain", "all")
    selected_company = request.args.get("company", "").strip()
    min_score = request.args.get("min_score", "").strip()
    sort = request.args.get("sort", "newest")

    try:
        ensure_demo_content()

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
            offline=False,
            offline_error=None,
        )
    except Exception as exc:
        # Fallback to an offline demo view if the database is unreachable
        demo_companies = [SimpleNamespace(company_id=i + 1, name=c["name"]) for i, c in enumerate(DEMO_COMPANIES)]
        demo_company_lookup = {c.name: c for c in demo_companies}

        fallback_papers = []
        for i, p in enumerate(DEMO_PAPERS, start=1):
            company_link = SimpleNamespace(company=demo_company_lookup.get(p["company"]))
            paper_obj = SimpleNamespace(
                paper_id=i,
                title=p["title"],
                abstract=p["abstract"],
                research_domain=p["research_domain"],
                upload_date=None,
                file_path=p["file_path"],
                author=SimpleNamespace(name="Demo Author"),
                reviews=[],
                companies=[company_link],
                user_id=0,
            )
            fallback_papers.append(paper_obj)

        fallback_scores = {
            1: {"avg": 9.1, "count": 1},
            2: {"avg": 8.7, "count": 1},
        }

        domain_filters = sorted({p["research_domain"] for p in DEMO_PAPERS}.union(set(POPULAR_DOMAINS)))

        return render_template(
            "dashboard.html",
            title="Dashboard (offline demo)",
            papers=fallback_papers,
            score_map=fallback_scores,
            domains=domain_filters,
            companies=demo_companies,
            selected_domain="all",
            selected_company="",
            min_score="",
            sort="newest",
            query="",
            offline=True,
            offline_error="Database niet bereikbaar, tonen demo data. Detailpagina's zijn klikbaar maar niet schrijfbaar.",
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
        "title": "Attention Is All You Need",
        "abstract": "Introduce the Transformer architecture based solely on attention mechanisms, achieving state-of-the-art results in machine translation.",
        "file_path": "https://arxiv.org/pdf/1706.03762.pdf",
        "research_domain": "AI",
        "company": "Google Brain Research",
    },
    {
        "title": "Highly accurate protein structure prediction with AlphaFold",
        "abstract": "Deep learning system predicts 3D protein structures at atomic accuracy, transforming structural biology.",
        "file_path": "https://arxiv.org/pdf/2104.05514.pdf",
        "research_domain": "Biotech",
        "company": "DeepMind Research Lab",
    },
    {
        "title": "Graph Attention Networks",
        "abstract": "Applies masked self-attentional layers to graph-structured data, improving graph classification and node prediction.",
        "file_path": "https://arxiv.org/pdf/1710.10903.pdf",
        "research_domain": "AI",
        "company": "ETH Zurich AI Center",
    },
    {
        "title": "Proximal Policy Optimization Algorithms",
        "abstract": "Simplified policy gradient method with clipped objectives for stable and efficient reinforcement learning.",
        "file_path": "https://arxiv.org/pdf/1707.06347.pdf",
        "research_domain": "Robotics",
        "company": "OpenAI Robotics Lab",
    },
    {
        "title": "NeRF: Representing Scenes as Neural Radiance Fields",
        "abstract": "Neural radiance fields enable photorealistic novel view synthesis from sparse 2D images.",
        "file_path": "https://arxiv.org/pdf/2003.08934.pdf",
        "research_domain": "AI",
        "company": "UC Berkeley Visual Computing Lab",
    },
    {
        "title": "Neural Ordinary Differential Equations",
        "abstract": "Continuous-depth neural networks parameterized by ODEs for memory-efficient models and generative flows.",
        "file_path": "https://arxiv.org/pdf/1806.07366.pdf",
        "research_domain": "Data & Analytics",
        "company": "Vector Institute",
    },
    {
        "title": "Learning Transferable Visual Models From Natural Language Supervision",
        "abstract": "CLIP aligns vision and language via contrastive pretraining, enabling zero-shot recognition.",
        "file_path": "https://arxiv.org/pdf/2103.00020.pdf",
        "research_domain": "AI",
        "company": "Stanford AI Lab",
    },
    {
        "title": "Sim-to-Real Transfer of Robotic Control with Dynamics Randomization",
        "abstract": "Policy trained in simulation transfers to real robots by randomizing physical parameters.",
        "file_path": "https://arxiv.org/pdf/1710.06537.pdf",
        "research_domain": "Robotics",
        "company": "Carnegie Mellon Robotics Institute",
    },
    {
        "title": "FlashAttention: Fast and Memory-Efficient Exact Attention",
        "abstract": "IO-aware attention algorithm accelerates Transformers while preserving exactness.",
        "file_path": "https://arxiv.org/pdf/2205.14135.pdf",
        "research_domain": "AI",
        "company": "MIT CSAIL",
    },
    {
        "title": "Large Language Models are Zero-Shot Reasoners",
        "abstract": "Shows chain-of-thought prompting unlocks reasoning capabilities in large language models.",
        "file_path": "https://arxiv.org/pdf/2205.11916.pdf",
        "research_domain": "AI",
        "company": "Google Brain Research",
    },
    {
        "title": "Quantum Approximate Optimization Algorithm",
        "abstract": "QAOA provides a quantum-classical variational approach for combinatorial optimization.",
        "file_path": "https://arxiv.org/pdf/1411.4028.pdf",
        "research_domain": "Quantum",
        "company": "Caltech Quantum Science Center",
    },
    {
        "title": "AlphaStar: Grandmaster level in StarCraft II using multi-agent reinforcement learning",
        "abstract": "Multi-agent RL system reaches grandmaster level in a complex real-time strategy game.",
        "file_path": "https://arxiv.org/pdf/1907.01083.pdf",
        "research_domain": "AI",
        "company": "DeepMind Research Lab",
    },
    {
        "title": "Physics-Informed Neural Networks: A Deep Learning Framework for Solving Forward and Inverse Problems",
        "abstract": "PINNs embed physical laws into neural networks for simulation and control.",
        "file_path": "https://arxiv.org/pdf/1711.10561.pdf",
        "research_domain": "Energy",
        "company": "Imperial College Energy Futures Lab",
    },
    {
        "title": "Spatiotemporal Graph Convolutional Networks: A Deep Learning Framework for Traffic Forecasting",
        "abstract": "ST-GCN captures spatial and temporal correlations for accurate traffic prediction.",
        "file_path": "https://arxiv.org/pdf/1709.04875.pdf",
        "research_domain": "Mobility",
        "company": "Tsinghua Future Mobility Center",
    },
    {
        "title": "Masked Autoencoders Are Scalable Vision Learners",
        "abstract": "MAE demonstrates simple masked pretraining yields strong vision representations.",
        "file_path": "https://arxiv.org/pdf/2111.06377.pdf",
        "research_domain": "AI",
        "company": "Max Planck Institute for Intelligent Systems",
    },
    {
        "title": "SLAC: Stochastic Latent Actor-Critic",
        "abstract": "Model-based RL with stochastic latent variables enables sample-efficient control.",
        "file_path": "https://arxiv.org/pdf/1910.01083.pdf",
        "research_domain": "Robotics",
        "company": "TU Delft Robotics Institute",
    },
    {
        "title": "Quantum Supremacy Using a Programmable Superconducting Processor",
        "abstract": "Demonstration of a quantum processor performing a task beyond classical feasibility.",
        "file_path": "https://arxiv.org/pdf/1910.11333.pdf",
        "research_domain": "Quantum",
        "company": "NASA Jet Propulsion Laboratory",
    },
    {
        "title": "Training language models to follow instructions with human feedback",
        "abstract": "Introduces InstructGPT, fine-tuning with RLHF to align models to human intent.",
        "file_path": "https://arxiv.org/pdf/2203.02155.pdf",
        "research_domain": "AI",
        "company": "OpenAI Alignment Lab",
    },
    {
        "title": "Denoising Diffusion Probabilistic Models",
        "abstract": "Diffusion models achieve high-quality image synthesis through iterative denoising.",
        "file_path": "https://arxiv.org/pdf/2006.11239.pdf",
        "research_domain": "AI",
        "company": "UCL Centre for AI in Healthcare",
    },
    {
        "title": "Neural Radiance Fields in the Wild",
        "abstract": "Extends NeRF to handle unbounded real-world scenes with appearance variability.",
        "file_path": "https://arxiv.org/pdf/2008.02268.pdf",
        "research_domain": "AI",
        "company": "EPFL Neuroengineering Lab",
    },
]

DEMO_COMPANIES = [
    {"name": "Google Brain Research", "industry": "AI research"},
    {"name": "DeepMind Research Lab", "industry": "AI & biotech"},
    {"name": "ETH Zurich AI Center", "industry": "AI research"},
    {"name": "OpenAI Robotics Lab", "industry": "Robotics"},
    {"name": "UC Berkeley Visual Computing Lab", "industry": "Computer vision"},
    {"name": "Vector Institute", "industry": "ML research"},
    {"name": "Stanford AI Lab", "industry": "AI research"},
    {"name": "Carnegie Mellon Robotics Institute", "industry": "Robotics"},
    {"name": "MIT CSAIL", "industry": "Computer science"},
    {"name": "Caltech Quantum Science Center", "industry": "Quantum"},
    {"name": "Imperial College Energy Futures Lab", "industry": "Energy & climate"},
    {"name": "Tsinghua Future Mobility Center", "industry": "Mobility"},
    {"name": "Max Planck Institute for Intelligent Systems", "industry": "AI & robotics"},
    {"name": "TU Delft Robotics Institute", "industry": "Robotics"},
    {"name": "NASA Jet Propulsion Laboratory", "industry": "Space & quantum"},
    {"name": "OpenAI Alignment Lab", "industry": "AI alignment"},
    {"name": "UCL Centre for AI in Healthcare", "industry": "Healthcare AI"},
    {"name": "EPFL Neuroengineering Lab", "industry": "Neuroscience"},
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
            "score": 9.2,
            "comments": "Transformer paper die alles versimpelt en schaalbaar maakt. Research facility support was uitstekend.",
            "reviewer": demo_reviewer,
            "company": company_map.get("Google Brain Research"),
        },
        {
            "paper_title": DEMO_PAPERS[1]["title"],
            "score": 9.5,
            "comments": "AlphaFold blijft baanbrekend: indrukwekkende accuratesse vanuit de DeepMind facility.",
            "reviewer": demo_founder,
            "company": company_map.get("DeepMind Research Lab"),
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

POPULAR_DOMAINS = [
    "AI",
    "Robotics",
    "Biotech",
    "Climate",
    "Energy",
    "Security",
    "Data & Analytics",
    "Quantum",
    "Neuroscience",
    "Materials",
    "Mobility",
    "Space",
]
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
    try:
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
            offline=False,
            offline_error=None,
        )
    except Exception:
        # Offline/demo fallback for detail page
        demo_companies = [SimpleNamespace(company_id=i + 1, name=c["name"]) for i, c in enumerate(DEMO_COMPANIES)]
        demo_company_lookup = {c.name: c for c in demo_companies}

        # Map paper_id to demo paper (1..n)
        if paper_id < 1 or paper_id > len(DEMO_PAPERS):
            abort(404)

        p = DEMO_PAPERS[paper_id - 1]
        company_link = SimpleNamespace(company=demo_company_lookup.get(p["company"]))
        paper_obj = SimpleNamespace(
            paper_id=paper_id,
            title=p["title"],
            abstract=p["abstract"],
            research_domain=p["research_domain"],
            upload_date=None,
            file_path=p["file_path"],
            author=SimpleNamespace(name="Demo Author"),
            reviews=[],
            companies=[company_link],
            user_id=0,
        )

        # fallback review snippets
        sample_review = None
        if paper_id == 1:
            sample_review = SimpleNamespace(
                score=9.2,
                comments="Transformer paper met sterke research facility support, blijft een klassieker.",
                reviewer=SimpleNamespace(name="Guest Reviewer"),
                company=demo_company_lookup.get("Google Brain Research"),
                date_submitted=None,
            )
        elif paper_id == 2:
            sample_review = SimpleNamespace(
                score=9.5,
                comments="AlphaFold blijft een doorbraak vanuit DeepMind Research Lab.",
                reviewer=SimpleNamespace(name="Venture Partner"),
                company=demo_company_lookup.get("DeepMind Research Lab"),
                date_submitted=None,
            )

        reviews_sorted = [sample_review] if sample_review else []
        average_score = sample_review.score if sample_review else None
        score_count = 1 if sample_review else 0

        return render_template(
            "paper_detail.html",
            title=paper_obj.title,
            paper=paper_obj,
            companies=demo_companies,
            can_review=False,
            average_score=average_score,
            score_count=score_count,
            reviews_sorted=reviews_sorted,
            offline=True,
            offline_error="Database niet bereikbaar – tonen demo detail. Review indienen is tijdelijk uitgeschakeld.",
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
