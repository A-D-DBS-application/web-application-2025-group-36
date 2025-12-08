DROP TABLE IF EXISTS Review CASCADE;
DROP TABLE IF EXISTS PaperCompany CASCADE;
DROP TABLE IF EXISTS Paper CASCADE;
DROP TABLE IF EXISTS Company CASCADE;
DROP TABLE IF EXISTS "User" CASCADE;
CREATE TABLE "User" (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(100) CHECK (role IN ('writer', 'reviewer'))
);

CREATE TABLE Company (
    company_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    industry VARCHAR(255)
);

CREATE TABLE Paper (
    paper_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES "User"(user_id),
    title VARCHAR(255) NOT NULL,
    abstract TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PaperCompany (
    paper_id INT REFERENCES Paper(paper_id),
    company_id INT REFERENCES Company(company_id),
    PRIMARY KEY (paper_id, company_id)
);

CREATE TABLE Review (
    review_id SERIAL PRIMARY KEY,
    paper_id INT REFERENCES Paper(paper_id),
    reviewer_id INT REFERENCES "User"(user_id),
    score FLOAT,
    comments TEXT,
    date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

