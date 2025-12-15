[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/DxqGQVx4)

# Project A&D – DBS  
## ReviewR (Group 36)

---

## 1. Project Description

**ReviewR** is a web-based Minimum Viable Product (MVP) that supports and improves the
academic peer-review process by offering a **structured, transparent, and efficient**
way to evaluate research papers.

Researchers can upload academic papers and receive feedback, while users can
browse available papers and provide comments/reviews on these papers.

The platform aims to increase clarity, fairness, and usefulness of academic reviews.

---

## 2. Vision

> To create a world where academic knowledge flows freely and structured feedback
> accelerates innovation, collaboration, and real-world impact.

---

## 3. Core Functionalities (MVP Scope)

The application supports the following core features, aligned with the A&D / DBS
assignment requirements:

- User roles (researcher, user, company)
- Uploading academic papers (PDF)
- Browsing and filtering available papers
- Viewing detailed paper information
- Submitting structured reviews
- AI-analyzed papers based on **academic quality** and **business relevance**
- Linking papers to external organizations or companies
- Companies can also log in themself and show in which papers they are interested in.
- Persistent data storage using a relational database

Security features (advanced authentication, payments, messaging) are intentionally
kept minimal, as allowed for an MVP.

---

## 4. Algorithmic Component – AI-Assisted Analysis

ReviewR includes an **AI-assisted analysis component** that adds value beyond basic CRUD
functionality.

### Purpose
- Support reviewers with an initial structured evaluation
- Improve consistency and speed of the review process

### Output
- Academic score
- Business relevance score
- Short summary
- Strengths and weaknesses

### Important Notes
- The AI component acts as **decision support**, not as an autonomous evaluator
- Final assessments remain under human control
- The AI is fully integrated into the application workflow

---

## 5. Database Design

The application uses a **PostgreSQL relational database** (Supabase), implemented using
SQLAlchemy.

### Main Entities
- User
- Paper
- Review
- Company
- PaperCompany (association table)
- Complaint

The database is normalized and designed to be **scalable** for future extensions.

📦 A database dump is included  
(backup date: **09/12/2025 – 09:40**)

---

## 6. Technology Stack

- Backend: Flask (Python)
- Frontend: HTML, Tailwind CSS
- Database: PostgreSQL (Supabase)
- ORM: SQLAlchemy
- AI Analysis: Google Gemini API
- Storage: Supabase Storage
- Deployment: Render

---

## 7. Agile Development & Validation

The project was developed following **Agile principles**, using multiple sprints with
iterative improvements.

Feedback was collected through:
- User testing (Google forms & Render)
- Feedback and experience sessions
- Continuous refinement of UI and functionality

### Kanban Board
https://miro.com/app/board/uXjVJwVsXsc=/

### UI Prototype (Lovable)
https://lovable.dev/projects/4b212f05-6181-4bad-b4f4-01cc5bc567d5

---

## 8. Setup – AI Analysis Configuration

To enable AI analysis locally, create a `.flaskenv` file with the following content:
> FLASK_APP=run.py
> FLASK_ENV=development
> GEMINI_API_KEY=AIxxxx --> Key you made yourself.
> DATABASE_URL=postgresql://postgres.ebokqkhwotfewvpsfemj:3R9TrLYvLG7lIx7Y@aws-1-eu-west-1.pooler.supabase.com:6543/postgres

Create a Gemini API key here:  
https://aistudio.google.com/api-keys

---

## 9. Additional Links & Resources

### Supabase Project
https://supabase.com/dashboard/project/ebokqkhwotfewvpsfemj

### Test Users & Feedback
https://docs.google.com/spreadsheets/d/11K7iOIe6oSJGhSPdlgt530r-ltxOYVHAc8Jt30kQidU/edit


---

