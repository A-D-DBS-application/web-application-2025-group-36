from . import db

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
    papers = db.relationship('Paper', backref='author', lazy=True)
    reviews = db.relationship('Review', backref='reviewer', lazy=True)

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

    papers = db.relationship('PaperCompany', back_populates='company')


# ================================
# PAPER
# ================================
class Paper(db.Model):
    __tablename__ = "Paper"

    paper_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.user_id', ondelete='CASCADE'))
    title = db.Column(db.String(255), nullable=False)
    abstract = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    reviews = db.relationship('Review', backref='paper', lazy=True)
    companies = db.relationship('PaperCompany', back_populates='paper')

    def __repr__(self):
        return f"<Paper {self.title}>"


# ================================
# PAPERCOMPANY (koppeltabel N-M)
# ================================
class PaperCompany(db.Model):
    __tablename__ = "PaperCompany"

    paper_id = db.Column(db.Integer, db.ForeignKey('Paper.paper_id', ondelete='CASCADE'), primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('Company.company_id', ondelete='CASCADE'), primary_key=True)

    # bidirectionele relaties
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
    score = db.Column(db.Float)
    comments = db.Column(db.Text)
    date_submitted = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Review Paper={self.paper_id}, Score={self.score}>"

