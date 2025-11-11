from flask import Blueprint, render_template, request, redirect, url_for, flash
<<<<<<< HEAD
from .config import Config, DUMMY_PAPERS, DUMMY_COMPANIES, LINKS
=======
from .models import db, Paper, Company, PaperCompany
>>>>>>> 44b9b62bbaac8296fc3093dc82f7b713cc3f4b48

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    """Landing page with navigation"""
    return render_template("index.html")


@bp.route("/author", methods=["GET", "POST"])
def author():
    """Author page: list papers, link paper to company"""
    papers = Paper.query.all()
    companies = Company.query.all()

    if request.method == "POST":
        paper_id = int(request.form.get("paper_id"))
        company_id = int(request.form.get("company_id"))

        existing_link = PaperCompany.query.filter_by(paper_id=paper_id, company_id=company_id).first()
        if existing_link:
            flash("Deze paper is al gelinkt aan dit bedrijf.", "warning")
        else:
            link = PaperCompany(paper_id=paper_id, company_id=company_id)
            db.session.add(link)
            db.session.commit()
            flash("Paper succesvol gelinkt aan bedrijf!", "success")

        return redirect(url_for("main.author"))

    # Build a list of linked pairs
    linked = [
        {"paper": link.paper.title, "company": link.company.name}
        for link in PaperCompany.query.all()
    ]

    return render_template(
        "author.html",
        papers=papers,
        companies=companies,
        links=linked,
    )


@bp.route("/company")
def company():
    """Company page: show companies and linked papers"""
    companies = Company.query.all()

    company_view = []
    for comp in companies:
        linked_papers = [link.paper.title for link in comp.paper_links]
        company_view.append({"company": comp.name, "papers": linked_papers})

    return render_template("company.html", company_view=company_view)