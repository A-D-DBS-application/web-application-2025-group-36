from flask import Blueprint, render_template, request, redirect, url_for, flash
from .config import Config, DUMMY_PAPERS, DUMMY_COMPANIES, LINKS

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    """
    Landing page met 2 knoppen:
    - 'Ik ben schrijver' → /author
    - 'Ik ben bedrijf'  → /company
    """
    return render_template("index.html")


@bp.route("/author", methods=["GET", "POST"])
def author():
    """
    Eenvoudige 'schrijver' pagina:
    - toont lijst met eigen/alle papers (dummy)
    - klein formulier om paper aan bedrijf te koppelen (MVP)
    """
    if request.method == "POST":
        paper_id = int(request.form.get("paper_id"))
        company_id = int(request.form.get("company_id"))
        LINKS.append((paper_id, company_id))
        flash("Paper succesvol gelinkt aan bedrijf (dummy, in-memory).", "success")
        return redirect(url_for("main.author"))

    # Bouw een overzicht van bestaande links voor weergave
    linked = []
    for (p_id, c_id) in LINKS:
        p = next((x for x in DUMMY_PAPERS if x["id"] == p_id), None)
        c = next((x for x in DUMMY_COMPANIES if x["id"] == c_id), None)
        if p and c:
            linked.append({"paper": p["title"], "company": c["name"]})

    return render_template(
        "author.html",
        papers=DUMMY_PAPERS,
        companies=DUMMY_COMPANIES,
        links=linked,
    )


@bp.route("/company")
def company():
    """
    Eenvoudige 'bedrijf' pagina:
    - toont bedrijven (dummy)
    - toont welke papers al gelinkt zijn (dummy)
    """
    # Bouw per bedrijf een lijst met gelinkte papers
    company_view = []
    for comp in DUMMY_COMPANIES:
        comp_links = []
        for (p_id, c_id) in LINKS:
            if c_id == comp["id"]:
                p = next((x for x in DUMMY_PAPERS if x["id"] == p_id), None)
                if p:
                    comp_links.append(p["title"])
        company_view.append({"company": comp["name"], "papers": comp_links})

    return render_template("company.html", company_view=company_view)