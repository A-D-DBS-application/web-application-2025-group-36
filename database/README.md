# REVIEWR – Database Documentation

This document describes the **database structure, entities, and relationships** of the
REVIEWR web application.  
The database is designed to support the core MVP functionality while remaining
**normalized, scalable, and extensible**.

---

## 1. Overview

REVIEWR is a web platform that connects **academic research** with **reviewers and
external organizations**.

The database supports:
- User management (researchers, users & companies)
- Storage of academic papers and metadata
- Linking papers to companies
- Structured reviews
- Complaint and moderation tracking
- AI-assisted analysis results

The database runs on **PostgreSQL**, managed via **Supabase**, and is accessed through
**SQLAlchemy ORM**.

---

## 2. Database Tables

### 2.1 `users`

Stores user accounts and roles within the platform.

| Column | Type | Description |
|------|------|-------------|
| user_id | SERIAL (PK) | Unique user identifier |
| name | VARCHAR | User name |
| email | VARCHAR (UNIQUE) | User email address |
| role | VARCHAR | User role (`researcher`, `user`) |

---

### 2.2 `company`

Represents external organizations linked to academic papers.

| Column | Type | Description |
|------|------|-------------|
| company_id | SERIAL (PK) | Unique company identifier |
| name | VARCHAR | Company name |
| industry | VARCHAR | Industry or sector |

---

### 2.3 `paper`

Stores uploaded academic papers and related metadata.

| Column | Type | Description |
|------|------|-------------|
| paper_id | SERIAL (PK) | Unique paper identifier |
| user_id | INT (FK → users.user_id) | Author of the paper |
| title | VARCHAR | Paper title |
| abstract | TEXT | Paper abstract |
| upload_date | TIMESTAMP | Date of upload |
| file_path | VARCHAR | Storage path of the PDF |
| research_domain | VARCHAR | Research domain |
| ai_business_score | INT | AI-generated business relevance score |
| ai_academic_score | INT | AI-generated academic score |
| ai_summary | TEXT | AI-generated summary |
| ai_strengths | TEXT | AI-detected strengths |
| ai_weaknesses | TEXT | AI-detected weaknesses |
| ai_status | VARCHAR | AI analysis status |

---

### 2.4 `papercompany`

Association table implementing the **many-to-many relationship** between papers and
companies.

| Column | Type | Description |
|------|------|-------------|
| paper_id | INT (FK → paper.paper_id) | Linked paper |
| company_id | INT (FK → company.company_id) | Linked company |
| relation_type | VARCHAR | Nature of the relationship |
| **PRIMARY KEY** | (paper_id, company_id) | Composite primary key |

---

### 2.5 `review`

Stores structured reviews submitted by reviewers.

| Column | Type | Description |
|------|------|-------------|
| review_id | SERIAL (PK) | Unique review identifier |
| paper_id | INT (FK → paper.paper_id) | Reviewed paper |
| reviewer_id | INT (FK → users.user_id) | Reviewer |
| score | FLOAT | Review score |
| comments | TEXT | Review comments |
| date_submitted | TIMESTAMP | Submission date |
| company_id | INT (FK → company.company_id) | Optional company context |

---

### 2.6 `complaint`

Stores complaints related to papers for moderation purposes.

| Column | Type | Description |
|------|------|-------------|
| complaint_id | SERIAL (PK) | Unique complaint identifier |
| paper_id | INT (FK → paper.paper_id) | Related paper |
| reporter_name | VARCHAR | Name of reporter |
| reporter_email | VARCHAR | Email of reporter |
| category | VARCHAR | Complaint category |
| description | TEXT | Complaint description |
| created_at | TIMESTAMP | Creation timestamp |

---

### 2.7 `alembic_version`

Tracks database migration versions.

| Column | Type | Description |
|------|------|-------------|
| version_num | VARCHAR (PK) | Alembic migration identifier |

---

## 3. Relationships Overview

- **User → Paper**  
  One user (author) can upload multiple papers (1-to-many)

- **Paper ↔ Company**  
  Many-to-many relationship implemented via `papercompany`

- **User → Review → Paper**  
  A reviewer can submit multiple reviews; a paper can receive multiple reviews

- **Company → Review (optional)**  
  Reviews can optionally be linked to a company context

- **Paper → Complaint**  
  A paper can have multiple complaints (1-to-many)

---

## 4. Design Considerations

- Fully normalized relational schema
- Clear separation of concerns
- Referential integrity enforced via foreign keys
- Scalable design for future extensions (notifications, moderation, analytics)
- AI-generated data stored separately from human reviews

---

## 5. Backup & Restore

- **Backup:** `database_backup.sql` included in the repository  
- **Restore:** via Supabase SQL Editor or `psql`

```bash
psql -h <host> -U <user> -d <database> -f database_backup.sql
