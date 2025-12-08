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

--Here is some testdata
INSERT INTO "User" (name, email, role) VALUES
('Emma Vermeulen', 'emma@ugent.be', 'writer'),
('Tom Janssens', 'tom@ugent.be', 'writer'),
('Lotte Peeters', 'lotte@ugent.be', 'reviewer'),
('Dries Van Den Bossche', 'dries@ugent.be', 'reviewer');

-- Companies
INSERT INTO Company (name, industry) VALUES
('AI SpinOff', 'Artificial Intelligence'),
('BioTechLab', 'Biotechnology'),
('GreenFuture', 'Sustainability');

-- Papers
INSERT INTO Paper (user_id, title, abstract) VALUES
(1, 'AI in Business Innovation', 'A study on the use of AI to accelerate business model innovation.'),
(2, 'Sustainable Packaging Solutions', 'Exploring biodegradable materials for modern packaging.');

-- PaperCompany links
INSERT INTO PaperCompany (paper_id, company_id) VALUES
(1, 1),
(2, 3);

-- Reviews
INSERT INTO Review (paper_id, reviewer_id, score, comments) VALUES
(1, 3, 8.5, 'Good relevance for startups, some improvements needed in the dataset.'),
(2, 4, 9.2, 'Strong potential for green startups and sustainability impact.');
