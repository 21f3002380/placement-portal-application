import os
from flask import render_template, request, redirect, url_for, send_from_directory, abort, flash
from flask_login import login_user,logout_user,login_required,current_user
from werkzeug.utils import secure_filename
from functools import wraps
from app import app,db,bcrypt
from models import User, Student, Company, PlacementDrive, Application
from config import Config

def role_required(*roles): #to check if the role is proper or not
    def decorator(f):
        @wraps(f)
        def wrapped(*args,**kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args,**kwargs)
        return wrapped
    return decorator

def file_allowed(filename): #checking the file type
    return '.' in filename and filename.rsplit('.',1)[1].lower() == 'pdf'

@app.route('/')
def index():
    if current_user.is_authenticated: #user authentication
        role=current_user.role.lower()
        return redirect(url_for(f'{role}_dashboard'))
    return redirect(url_for('login'))

@app.route('/login',methods=['GET','POST'])
def login(): #login functionality linked with HTML through rendering
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method=='POST':
        email=request.form.get('email','').strip().lower()
        password=request.form.get('password','')
        user=User.query.filter_by(email=email).first()
        
        if not user or not bcrypt.check_password_hash(user.password,password):
            flash('Invalid email or password!!!')
            return render_template('auth/login.html')
        
        if not user.is_active:
            flash('Your account is not active!!!')
            return render_template('auth/login.html')

        if user.role=='company':
            if not user.company.is_approved or user.company.is_blacklisted:
                flash('Admin approval pending for your account')
                return render_template('auth/login.html')
            
        if user.role=='student' and user.student.is_blacklisted:
            flash('You have been blacklisted!!!')
            return render_template('auth/login.html')
        
        login_user(user)
        return redirect(url_for('index'))
    
    return render_template('auth/login.html')

@app.route('/register',methods=['GET','POST']) #register functionality
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method=='POST':
        email=request.form.get('email','').strip().lower()
        password=request.form.get('password','')
        role=request.form.get('role','')

        if role not in ('student','company'):
            flash('Invalid Role !!!')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists!!!')
            return render_template('auth/register.html')
        
        hashed_pw=bcrypt.generate_password_hash(password).decode('utf-8')
        user=User(email=email,password=hashed_pw,role=role)
        db.session.add(user)
        db.session.flush()

        if role=='student':
            name=request.form.get('name','').strip()
            roll_number=request.form.get('roll_number','').strip()

            if not name or not roll_number:
                db.session.rollback()
                flash('Name and roll number are required!!')
                return render_template('auth/register.html')
            
            if Student.query.filter_by(roll_number=roll_number).first():
                db.session.rollback()
                flash('Roll number already registered!!')
                return render_template('auth/register.html')
            
            student=Student(
                user_id=user.id,
                name=name,
                roll_number=roll_number,
                department=request.form.get('department',''),
                cgpa=float(request.form.get('cgpa')) if request.form.get('cgpa') else None,
                skills=request.form.get('skills','').strip()
            )
            db.session.add(student)
            db.session.flush()

            resume=request.files.get('resume')
            if resume and file_allowed(resume.filename):
                filename=secure_filename(f"{roll_number}.pdf")
                os.makedirs(Config.UPLOAD_FOLDER,exist_ok=True)
                resume.save(os.path.join(Config.UPLOAD_FOLDER,filename))
                student.resume_filename=filename
        
        elif role == 'company':
            company_name=request.form.get('company_name','').strip()
            if not company_name:
                db.session.rollback()
                flash('Company name is required!!')
                return render_template('auth/register.html')
            
            company=Company(
                user_id=user.id,
                company_name=company_name,
                hr_contact=request.form.get('hr_contact','').strip(),
                website=request.form.get('website','').strip(),
                description=request.form.get('description','').strip()
            )
            db.session.add(company)
        db.session.commit()

        if role=='student':
            flash("Registration is successful! Please log in!!")
        else:
            flash('Registration submitted! Wait for admin approval')
        return redirect(url_for('login'))
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    return "wait for some time!!"

@app.route('/company/dashboard')
@login_required
@role_required('company')
def company_dashboard():
    return "wait for some time!!"

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    return "wait for some time!!"