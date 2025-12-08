-- Verwijder ALLES en maak opnieuw aan
DROP TABLE IF EXISTS Review CASCADE;
DROP TABLE IF EXISTS Complaint CASCADE;
DROP TABLE IF EXISTS PaperCompany CASCADE;
DROP TABLE IF EXISTS Paper CASCADE;
DROP TABLE IF EXISTS Company CASCADE;
DROP TABLE IF EXISTS "User" CASCADE;

-- USER tabel
CREATE TABLE "User" (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Researcher', 'Reviewer', 'Company', 'User', 'System/Admin', 'Founder'))
);

-- COMPANY tabel
CREATE TABLE Company (
    company_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(255)
);

-- PAPER tabel
CREATE TABLE Paper (
    paper_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES "User"(user_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    abstract TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500) NOT NULL,
    research_domain VARCHAR(255) NOT NULL,
    ai_business_score FLOAT,
    ai_academic_score FLOAT,
    ai_summary TEXT,
    ai_strengths TEXT,
    ai_weaknesses TEXT,
    ai_status VARCHAR(50) DEFAULT 'pending'
);

-- PAPERCOMPANY tabel - MET relation_type
CREATE TABLE PaperCompany (
    paper_id INT REFERENCES Paper(paper_id) ON DELETE CASCADE,
    company_id INT REFERENCES Company(company_id) ON DELETE CASCADE,
    relation_type VARCHAR(100) NOT NULL DEFAULT 'facility',
    PRIMARY KEY (paper_id, company_id, relation_type)
);

-- REVIEW tabel
CREATE TABLE Review (
    review_id SERIAL PRIMARY KEY,
    paper_id INT REFERENCES Paper(paper_id) ON DELETE CASCADE,
    reviewer_id INT REFERENCES "User"(user_id) ON DELETE CASCADE,
    company_id INT REFERENCES Company(company_id) ON DELETE SET NULL,
    score FLOAT CHECK (score >= 0 AND score <= 10),
    comments TEXT,
    date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- COMPLAINT tabel
CREATE TABLE Complaint (
    complaint_id SERIAL PRIMARY KEY,
    paper_id INT REFERENCES Paper(paper_id) ON DELETE CASCADE,
    reporter_name VARCHAR(255),
    reporter_email VARCHAR(255),
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);