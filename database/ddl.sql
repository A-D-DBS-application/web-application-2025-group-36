-- DROP TABLES (zorg dat ze in de juiste volgorde vallen ivm foreign keys)
DROP TABLE IF EXISTS Review CASCADE;
DROP TABLE IF EXISTS Complaint CASCADE;
DROP TABLE IF EXISTS PaperCompany CASCADE;
DROP TABLE IF EXISTS Paper CASCADE;
DROP TABLE IF EXISTS Company CASCADE;
DROP TABLE IF EXISTS "User" CASCADE;

-- User tabel
CREATE TABLE "User" (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('writer','reviewer'))
);

-- Company tabel
CREATE TABLE Company (
    company_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(255)
);

-- Paper tabel
CREATE TABLE Paper (
    paper_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES "User"(user_id),
    title VARCHAR(255) NOT NULL,
    abstract TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(255) NOT NULL,
    research_domain VARCHAR(255) NOT NULL,
    ai_business_score INT,
    ai_academic_score INT,
    ai_summary TEXT,
    ai_strengths TEXT,
    ai_weaknesses TEXT,
    ai_status VARCHAR(50)
);

-- PaperCompany tabel
CREATE TABLE PaperCompany (
    paper_id INT REFERENCES Paper(paper_id),
    company_id INT REFERENCES Company(company_id),
    relation_type VARCHAR(100) NOT NULL DEFAULT 'related',
    PRIMARY KEY (paper_id, company_id)
);

-- Review tabel
CREATE TABLE Review (
    review_id SERIAL PRIMARY KEY,
    paper_id INT REFERENCES Paper(paper_id),
    reviewer_id INT REFERENCES "User"(user_id),
    score FLOAT,
    comments TEXT,
    date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    company_id INT REFERENCES Company(company_id)
);

-- Complaint tabel
CREATE TABLE Complaint (
    complaint_id SERIAL PRIMARY KEY,
    paper_id INT REFERENCES Paper(paper_id),
    reporter_name VARCHAR(255),
    reporter_email VARCHAR(255),
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
<<<<<<< HEAD

-- Alembic versie tabel
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(50) NOT NULL,
    PRIMARY KEY (version_num)
);
=======
>>>>>>> parent of 0afb720 (Update ddl.sql)
