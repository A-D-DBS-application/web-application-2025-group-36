# REVIEWR Database Documentation

This document describes the structure and relationships of the database for the REVIEWR web application.

---

## Overview

REVIEWR is a platform connecting academic research with companies.  
The database supports:

- User management (writers and reviewers)  
- Storage of papers and metadata  
- Linking papers to companies  
- Reviews by users  
- Complaint tracking

The database runs on **PostgreSQL** (Supabase-managed).

---

## Tables and Columns

### 1. users
- **user_id** (SERIAL, PRIMARY KEY) – Unique ID for each user  
- **name** (VARCHAR, NOT NULL) – Name of the user  
- **email** (VARCHAR, UNIQUE, NOT NULL) – Email of the user  
- **role** (VARCHAR, NOT NULL, CHECK in ['writer','reviewer']) – Role of the user  

### 2. company
- **company_id** (SERIAL, PRIMARY KEY) – Unique ID for each company  
- **name** (VARCHAR, NOT NULL) – Company name  
- **industry** (VARCHAR) – Industry or sector  

### 3. paper
- **paper_id** (SERIAL, PRIMARY KEY) – Unique ID for each paper  
- **user_id** (INT, FOREIGN KEY → users.user_id) – Author of the paper  
- **title** (VARCHAR, NOT NULL) – Paper title  
- **abstract** (TEXT) – Paper abstract  
- **upload_date** (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP) – Upload date  
- **file_path** (VARCHAR, NOT NULL) – File path of the uploaded paper  
- **research_domain** (VARCHAR, NOT NULL) – Research domain  
- **ai_business_score** (INT) – AI-generated business relevance score  
- **ai_academic_score** (INT) – AI-generated academic score  
- **ai_summary** (TEXT) – AI-generated summary  
- **ai_strengths** (TEXT) – AI-detected strengths  
- **ai_weaknesses** (TEXT) – AI-detected weaknesses  
- **ai_status** (VARCHAR) – AI evaluation status  

### 4. papercompany
- **paper_id** (INT, FOREIGN KEY → paper.paper_id) – Paper ID  
- **company_id** (INT, FOREIGN KEY → company.company_id) – Company ID  
- **relation_type** (VARCHAR, DEFAULT 'related', NOT NULL) – Type of relationship  
- **PRIMARY KEY** (paper_id, company_id) – Composite primary key  

### 5. review
- **review_id** (SERIAL, PRIMARY KEY) – Unique review ID  
- **paper_id** (INT, FOREIGN KEY → paper.paper_id) – Paper being reviewed  
- **reviewer_id** (INT, FOREIGN KEY → users.user_id) – Reviewer of the paper  
- **score** (FLOAT) – Review score  
- **comments** (TEXT) – Review comments  
- **date_submitted** (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP) – Submission date  
- **company_id** (INT, FOREIGN KEY → company.company_id) – Optional company associated  

### 6. complaint
- **complaint_id** (SERIAL, PRIMARY KEY) – Unique complaint ID  
- **paper_id** (INT, FOREIGN KEY → paper.paper_id) – Paper related to the complaint  
- **reporter_name** (VARCHAR) – Name of the reporter  
- **reporter_email** (VARCHAR) – Email of the reporter  
- **category** (VARCHAR, DEFAULT 'General', NOT NULL) – Complaint category  
- **description** (TEXT, NOT NULL) – Complaint description  
- **created_at** (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP) – Date of submission  

### 7. alembic_version
- **version_num** (VARCHAR, PRIMARY KEY) – Tracks Alembic migration version  

---

## Relationships Overview

- **users → paper**: A user (writer) can author multiple papers (one-to-many).  
- **paper → papercompany → company**: A paper can be linked to multiple companies, and a company can be linked to multiple papers (many-to-many).  
- **users → review → paper**: A user (reviewer) can review multiple papers; a paper can have multiple reviews (many-to-many).  
- **company → review → paper**: A review can optionally be associated with a company.  
- **paper → complaint**: A paper can have multiple complaints (one-to-many).  

---

## Backup & Restore

- **Backup:** see `database_backup.sql` in the project.  
- **Restore:** via Supabase SQL Editor or `psql`:

