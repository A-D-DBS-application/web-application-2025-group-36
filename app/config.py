"""
Configuratie + dummy data.
Vervang dit later door Supabase queries.
"""

class Config:
    SECRET_KEY = "dev-only-dummy-secret"  # nodig voor flash messages/forms

# ------- DUMMY DATA (in-memory) -------
# Papers worden hier voorgesteld als minimale dicts.
DUMMY_PAPERS = [
    {"id": 1, "title": "Efficient Concrete Mix Design", "author": "A. Vermeer"},
    {"id": 2, "title": "Stormwater Infiltration in Urban Areas", "author": "M. De Bruyne"},
    {"id": 3, "title": "Wind Loads According to EN 1991-1-4", "author": "S. Pillaert"},
]

# Bedrijven idem.
DUMMY_COMPANIES = [
    {"id": 10, "name": "Provoost Engineering"},
    {"id": 11, "name": "Fluvius"},
    {"id": 12, "name": "Farys"},
]

# In-memory “links” tussen papers en bedrijven.
# Vorm: lijst van tuple (paper_id, company_id)
LINKS = []