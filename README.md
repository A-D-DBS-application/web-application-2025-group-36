[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/DxqGQVx4)
# REVIEWR – Web Application (Group 36)

REVIEWR is a web application that connects **academic research papers** with **companies**, allowing users to upload papers, perform **AI-based analysis**, write reviews, and manage complaints.  
The application was developed as a **Minimum Viable Product (MVP)** with scalability in mind.

---

## 1. Project Overview

REVIEWR supports:
- Uploading and downloading research papers
- Linking papers to one or more companies
- Writing academic and business-oriented reviews
- AI-powered paper analysis using Google Gemini
- Complaint tracking and moderation
- Role-based access (Researcher, User, Company, System/Admin & Founder)

The database is **fully normalized** and designed to be **scalable for future extensions**.

---

## 2. Database Design (SQLAlchemy)

### Main Entities
- **User**
- **Paper**
- **Review**
- **Company**
- **PaperCompany** (association table)
- **Complaint**

A PostgreSQL **database dump is included**.  
**Backup date:** 09/12/2025 – 09:40

---

## 3. Technology Stack

- **Backend:** Flask (Python)
- **Frontend:** HTML, Tailwind CSS
- **Database:** PostgreSQL (Supabase)
- **ORM:** SQLAlchemy
- **AI Analysis:** Google Gemini API
- **File Storage:** Supabase Storage
- **Deployment:** Render

---

## 4. Agile Development & Validation

The project was developed following **Agile principles**, using multiple sprints and iterative improvements.

Feedback was collected through:
- User testing (Google Forms & Render)
- Feedback and experience sessions
- Continuous refinement of UI and functionality

### Kanban Board (Miro)
https://miro.com/app/board/uXjVwVsXsc=/

---

## 5. UI Prototype

A UI prototype was created using **Lovable**:  
https://lovable.dev/projects/4b212f05-6181-4bad-b4f4-01cc5bc567d5

---

## 6. Local Installation & Setup

### 6.1 Prerequisites

Make sure the following are installed:
- Python **3.10 or higher**
- Git
- Internet access (for Supabase and Gemini API)

---

### 6.2 Clone the Repository

```bash
git clone https://github.com/A-D-DBS-application/web-application-2025-group-36.git
``` 

---

### 6.3 Create and Activate a Virtual Environment
```bash
python -m venv venv
``` 
- Windows: 
```bash
venv\Scripts\activate
``` 
- macOS/Linux:
```bash
source venv/bin/activate
``` 

---

### 6.4 Install Dependencies
```bash
pip install -r requirements.txt
``` 

---

## 7 Environment Configuration (AI Analysis)
Create a .flaskenv file in the root directory with the following content:
```bash
FLASK_APP=run.py
FLASK_ENV=development
GEMINI_API_KEY=AIxxxx
DATABASE_URL=postgresql://postgres.ebokqkhwotfewvpsfemj:Projectgroep36@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
``` 

Create a Gemini API key here:
https://aistudio.google.com/api-keys 

DO NOT COMMIT YOUR API KEY TO GITHUB (.gitignore)

---

## 8. Database & Storage
- Database hosting: Supabase (PostgreSQL)
- ORM: SQLAlchemy
- File storage: Supabase Storage
- A database dump is included for restoration if required

### Supabase Project Dashboard
https://supabase.com/dashboard/project/ebokqkhwotfewvpsfemj

---

## 9. Running the Application Locally
```bash
flask run
``` 

The application will be available at:
http://127.0.0.1:5000

---

## 10. Additional Resources
- Test Users & Feedback: https://docs.google.com/spreadsheets/d/11K7iOIe6oSJGhSPdlgt530r-ltxOYVHAc8Jt30kQidU/edit

---

## 11. Deployment
The application is deployed using Render.
Supabase is used for database management and file storage in production.

- Render: https://reviewr-project-aandd-dbs.onrender.com

---

## 12. Notes
- This project is an MVP, but the architecture supports future extensions
- The database schema is normalized and scalable
- AI analysis is optional and requires a valid Gemini API key

---
© 2025 – Group 36 – Project A&D DBS

cd web-application-2025-group-36

