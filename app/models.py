from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# ================================
# USER
# ================================
class User(db.Model):
    __tablename__ = "User"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(100), nullable=False)

    # Relationships
    papers = db.relationship(
        'Paper',
        backref='author',
        lazy=True,
        cascade="all, delete-orphan"
    )
    reviews = db.relationship(
        'Review',
        backref='reviewer',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"


# ================================
# COMPANY
# ================================
class Company(db.Model):
    __tablename__ = "Company"

    company_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(255))

    # 🔹 Interests die we net toegevoegd hebben (MVP)
    interests = db.Column(db.String(255))  # bijv. "AI,Robotics,Biotech"

    # 🔹 N-M relatie via koppeltabel PaperCompany
    papers = db.relationship(
        "PaperCompany",
        back_populates="company",
        cascade="all, delete-orphan"
    )



# ================================
# PAPER
# ================================
class Paper(db.Model):
    __tablename__ = "Paper"

    paper_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id', ondelete='CASCADE'))
    title = db.Column(db.String(255), nullable=False)
    abstract = db.Column(db.Text)
    research_domain = db.Column(db.String(120), default="General", nullable=False)
    upload_date = db.Column(db.DateTime, server_default=db.func.now())

    file_path = db.Column(db.String(512), nullable=False)
    
    @property
    def category_display(self):
        """Get readable category name - NO IMPORT HERE"""
        categories = [
            ('cs_ai', 'Computer Science - AI'),
            ('cs_se', 'Computer Science - SE'),
            ('cs_ds', 'Computer Science - Data Science'),
            ('math', 'Mathematics'),
            ('other', 'Other')
        ]
        for val, label in categories:
            if val == self.category:
                return label
        return self.category
    
    @property
    def research_domain_display(self):
        """Get readable domain name - NO IMPORT HERE"""
        domains = [
            ('AI', 'Artificial Intelligence'),
            ('Robotics', 'Robotics'),
            ('Software', 'Software Engineering'),
            ('Other', 'Other')
        ]
        for val, label in domains:
            if val == self.research_domain:
                return label
        return self.research_domain

    # Relationships
    reviews = db.relationship(
        'Review',
        backref='paper',
        lazy=True,
        cascade="all, delete-orphan"
    )

    companies = db.relationship(
        'PaperCompany',
        back_populates='paper',
        lazy=True,
        cascade="all, delete-orphan"
    )

    complaints = db.relationship(
        'Complaint',
        backref='paper',
        lazy=True,
        cascade="all, delete-orphan"
    )

    # AI fields
    ai_business_score = db.Column(db.Integer)
    ai_academic_score = db.Column(db.Integer)
    ai_summary = db.Column(db.Text)
    ai_strengths = db.Column(db.Text)
    ai_weaknesses = db.Column(db.Text)
    ai_status = db.Column(db.String(20), default="pending")

    def __repr__(self):
        return f"<Paper {self.paper_id}: {self.title}>"


# ================================
# PAPERCOMPANY (N-M TABLE)
# ================================
class PaperCompany(db.Model):
    __tablename__ = "PaperCompany"

    paper_id = db.Column(
        db.Integer,
        db.ForeignKey('Paper.paper_id', ondelete='CASCADE'),
        primary_key=True
    )
    company_id = db.Column(
        db.Integer,
        db.ForeignKey('Company.company_id', ondelete='CASCADE'),
        primary_key=True
    )

    relation_type = db.Column(db.String(20), nullable=False, default="facility")

    paper = db.relationship('Paper', back_populates='companies')
    company = db.relationship('Company', back_populates='papers')


# ================================
# REVIEW
# ================================
class Review(db.Model):
    __tablename__ = "Review"

    review_id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('Paper.paper_id', ondelete='CASCADE'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('User.user_id', ondelete='CASCADE'))
    company_id = db.Column(db.Integer, db.ForeignKey('Company.company_id', ondelete='SET NULL'), nullable=True)
    score = db.Column(db.Float)
    comments = db.Column(db.Text)
    date_submitted = db.Column(db.DateTime, server_default=db.func.now())

    company = db.relationship('Company')

    def __repr__(self):
        return f"<Review Paper={self.paper_id}, Score={self.score}>"


# ================================
# COMPLAINT
# ================================
class Complaint(db.Model):
    __tablename__ = "Complaint"

    complaint_id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('Paper.paper_id', ondelete='CASCADE'), nullable=False)
    reporter_name = db.Column(db.String(255))
    reporter_email = db.Column(db.String(255))
    category = db.Column(db.String(100), default="General", nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def __repr__(self):
        return f"<Complaint Paper={self.paper_id}, Category={self.category}>"
