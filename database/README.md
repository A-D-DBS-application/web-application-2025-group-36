# REVIEWR – Database Documentation

This document describes the **database structure, entities, and relationships** of the  
REVIEWR web application.

The database is designed to support the core MVP functionality while remaining  
**normalized, coherent, and extensible**, with a clear separation between conceptual
design and platform-specific implementation details.

---

## 1. Overview

REVIEWR is a web platform that connects **academic research** with **reviewers and
external organizations (companies)**.

The database supports:
- User management with multiple roles
- Storage of academic papers and metadata
- Linking papers to companies
- Expression of company interest in papers
- Structured reviews
- Complaint and moderation tracking
- Storage of AI-assisted analysis results

The database uses **PostgreSQL**, managed via **Supabase**, and is accessed through the  
**SQLAlchemy ORM** in the application backend.

---

## 2. Database Tables

### 2.1 `User`

Stores user accounts and roles within the platform.

| Column | Type | Description |
|------|------|-------------|
| user_id | SERIAL (PK) | Unique user identifier |
| name | VARCHAR | User name |
| email | VARCHAR (UNIQUE) | User email address |
| role | VARCHAR | User role (`Researcher`, `Reviewer`, `Company`, `User`, `Founder`, `System/Admin`) |

---

### 2.2 `Company`

Represents external organizations interacting with academic research.

| Column | Type | Description |
|------|------|-------------|
| company_id | SERIAL (PK) | Unique company identifier |
| name | VARCHAR (UNIQUE) | Company name |
| industry | VARCHAR | Industry or sector |
| interests | VARCHAR | Comma-separated list of research domains of interest (MVP) |

---

### 2.3 `Paper`

Stores uploaded academic papers and related metadata.

| Column | Type | Description |
|------|------|-------------|
| paper_id | SERIAL (PK) | Unique paper identifier |
| user_id | INT (FK → User.user_id) | Author of the paper |
| title | VARCHAR | Paper title |
| abstract | TEXT | Paper abstract |
| research_domain | VARCHAR | Research domain |
| upload_date | TIMESTAMP | Date of upload |
| file_path | VARCHAR | Storage path of the PDF |
| ai_business_score | INT | AI-generated business relevance score |
| ai_academic_score | INT | AI-generated academic score |
| ai_summary | TEXT | AI-generated summary |
| ai_strengths | TEXT | AI-detected strengths |
| ai_weaknesses | TEXT | AI-detected weaknesses |
| ai_status | VARCHAR | AI analysis status |

---

### 2.4 `PaperCompany`

Association table implementing the **many-to-many relationship** between papers and
companies.

| Column | Type | Description |
|------|------|-------------|
| paper_id | INT (FK → Paper.paper_id) | Linked paper |
| company_id | INT (FK → Company.company_id) | Linked company |
| **PRIMARY KEY** | (paper_id, company_id) | Composite primary key |

> This table represents a **pure relational link** without additional semantics.

---

### 2.5 `CompanyInterest`

Stores expressions of interest from companies in specific papers.

| Column | Type | Description |
|------|------|-------------|
| company_id | INT (FK → Company.company_id) | Interested company |
| paper_id | INT (FK → Paper.paper_id) | Paper of interest |
| created_at | TIMESTAMP | Timestamp of interest |
| **PRIMARY KEY** | (company_id, paper_id) | Composite primary key |

---

### 2.6 `Review`

Stores structured reviews submitted by reviewers.

| Column | Type | Description |
|------|------|-------------|
| review_id | SERIAL (PK) | Unique review identifier |
| paper_id | INT (FK → Paper.paper_id) | Reviewed paper |
| reviewer_id | INT (FK → User.user_id) | Reviewer |
| score | FLOAT | Review score |
| comments | TEXT | Review comments |
| date_submitted | TIMESTAMP | Submission date |
| company_id | INT (FK → Company.company_id) | Optional company context |

---

### 2.7 `Complaint`

Stores complaints related to papers for moderation purposes.

| Column | Type | Description |
|------|------|-------------|
| complaint_id | SERIAL (PK) | Unique complaint identifier |
| paper_id | INT (FK → Paper.paper_id) | Related paper |
| reporter_name | VARCHAR | Name of reporter |
| reporter_email | VARCHAR | Email of reporter |
| category | VARCHAR | Complaint category |
| description | TEXT | Complaint description |
| created_at | TIMESTAMP | Creation timestamp |

---

### 2.8 `alembic_version`

Tracks database migration versions managed by Flask-Migrate.

| Column | Type | Description |
|------|------|-------------|
| version_num | VARCHAR (PK) | Alembic migration identifier |

---

## 3. Relationships Overview

- **User → Paper**  
  One user (author) can upload multiple papers (1-to-many)

- **Paper ↔ Company**  
  Many-to-many relationship implemented via `PaperCompany`

- **Company ↔ Paper (Interest)**  
  Many-to-many relationship implemented via `CompanyInterest`

- **User → Review → Paper**  
  A reviewer can submit multiple reviews; a paper can receive multiple reviews

- **Company → Review (optional)**  
  Reviews can optionally be linked to a company context

- **Paper → Complaint**  
  A paper can have multiple complaints (1-to-many)

---

## 4. Design Considerations

- Fully normalized relational schema
- Clear separation between:
  - relational links (`PaperCompany`)
  - semantic interactions (`CompanyInterest`)
- Referential integrity enforced via foreign keys
- Cascading deletes to prevent orphan records
- AI-generated data stored separately from human evaluations
- Design aligned with ORM models and application routes

---

## 5. Schema & Reproducibility

- The logical database schema is provided in `ddl.sql`
- A visual representation is provided in `ERD_Final Delivery.png`
- The database dump is from 18/12/2025, 12:36 and is provided in `Dataabse_dump.sql`

No physical database dump is included, as the project uses a **managed PostgreSQL
platform (Supabase)**.  
This avoids platform-specific artifacts and ensures that the database design remains
**clear, reproducible, and focused on the student-designed schema**.
