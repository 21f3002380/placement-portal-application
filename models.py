from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin,db.Model):
    __tablename__="users"

    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(120),unique=True,nullable=False)
    password=db.Column(db.String(512),nullable=False)
    role=db.Column(db.String(20),nullable=False) # Admin/Student/Company

    is_active=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

    student=db.relationship("Student",backref="user",uselist=False)
    company=db.relationship("Company",backref="user",uselist=False)


class Student(db.Model):
    __tablename__="students"

    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False,unique=True)

    name=db.Column(db.String(100),nullable=False)
    roll_number=db.Column(db.String(50),unique=True,nullable=False)
    branch=db.Column(db.String(50))
    cgpa=db.Column(db.Float)
    resume_link=db.Column(db.String(300))

    applications=db.relationship("Application",backref="student",lazy=True)

class Company(db.Model):
    __tablename__="companies"

    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False,unique=True)

    company_name=db.Column(db.String(120),nullable=False)
    description=db.Column(db.Text)
    website=db.Column(db.String(200))
    is_approved=db.Column(db.Boolean,default=False)

    drives=db.relationship("PlacementDrive",backref="company",lazy=True)

class PlacementDrive(db.Model):
    __tablename__="placement_drives"

    id=db.Column(db.Integer,primary_key=True)
    company_id=db.Column(db.Integer,db.ForeignKey("companies.id"),nullable=False)

    title = db.Column(db.String(150),nullable=False)
    job_role=db.Column(db.String(120),nullable=False)
    package=db.Column(db.Float)
    eligibility_cgpa=db.Column(db.Float)
    drive_date=db.Column(db.DateTime)
    drive_status=db.Column(db.String(20),default="Open") #status of drive - Open/Closed
    description=db.Column(db.Text)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

    applications=db.relationship("Application",backref="drive",lazy=True)
    
class Application(db.Model):
    __tablename__="applications"

    id=db.Column(db.Integer,primary_key=True)

    student_id=db.Column(db.Integer,db.ForeignKey("students.id"),nullable=False)
    drive_id=db.Column(db.Integer,db.ForeignKey("placement_drives.id"),nullable=False)

    application_status=db.Column(db.String(20),default="Applied") # Application process stages - Applied/Shortlisted/Interview/Rejected/Offered
    #application_result=db.Column(db.String(30)) Final outcome after interviews (before and during interviews, it shows None) - Selected/Rejected/Waiting
    remark=db.Column(db.Text) #Company Remarks

    applied_at=db.Column(db.DateTime,default=datetime.utcnow)

    __table_args__=(db.UniqueConstraint("student_id","drive_id",name="unique_student_drive"),)

    #student=db.relationship("Student",backref="applications")
    #drive=db.relationship("PlacementDrive",backref="applications")

class PlacementStats(db.Model):
    __tablename__="placement_stats"

    id=db.Column(db.Integer,primary_key=True)
    year=db.Column(db.Integer,unique=True)
    total_students=db.Column(db.Integer)
    students_placed=db.Column(db.Integer)
    highest_package=db.Column(db.Float)
    average_package=db.Column(db.Float)
    companies_visited=db.Column(db.Integer)