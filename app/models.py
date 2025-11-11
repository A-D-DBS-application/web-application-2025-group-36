from flask_sqlalchemy import SQLAlchemy
<<<<<<< HEAD
from datetime import datetime

=======
>>>>>>> 44b9b62bbaac8296fc3093dc82f7b713cc3f4b48
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "User"

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(100), nullable=False)

    # Relaties
    papers = db.relationship("Paper", back_populates="author", cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="reviewer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.name}, role={self.role}>"


class Company(db.Model):
    __tablename__ = "Company"

    company_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(255))

    # Relatie via association table
    papers = db.relationship("PaperCompany", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.name}>"


class Paper(db.Model):
    __tablename__ = "Paper"

    paper_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id'))
    title = db.Column(db.String(255), nullable=False)
    abstract = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaties
    author = db.relationship("User", back_populates="papers")
    reviews = db.relationship("Review", back_populates="paper", cascade="all, delete-orphan")
    companies = db.relationship("PaperCompany", back_populates="paper", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Paper {self.title}>"


class PaperCompany(db.Model):
    __tablename__ = "PaperCompany"

    paper_id = db.Column(db.Integer, db.ForeignKey('Paper.paper_id'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('Company.company_id'), primary_key=True)

    # Relaties
    paper = db.relationship("Paper", back_populates="companies")
    company = db.relationship("Company", back_populates="papers")

    def __repr__(self):
        return f"<PaperCompany paper_id={self.paper_id}, company_id={self.company_id}>"


class Review(db.Model):
    __tablename__ = "Review"

    review_id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('Paper.paper_id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('User.user_id'))
    score = db.Column(db.Float)
    comments = db.Column(db.Text)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaties
    paper = db.relationship("Paper", back_populates="reviews")
    reviewer = db.relationship("User", back_populates="reviews")

    def __repr__(self):
        return f"<Review paper_id={self.paper_id}, reviewer_id={self.reviewer_id}, score={self.score}>"

