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
    return render_template('admin/dashboard.html',
                           total_companies=Company.query.count(),
                           total_students=Student.query.count(),
                           total_drives=PlacementDrive.query.count(),
                           total_applications=Application.query.count(),
                           pending_companies=Company.query.filter_by(is_approved=False,is_blacklisted=False).all(),
                           pending_drives=PlacementDrive.query.filter_by(approval_status='pending').all(),
                           recent_applications=Application.query.order_by(Application.applied_at.desc()).limit(10).all(),
                           )
    return "wait for some time!!"

@app.route('/admin/companies')
@login_required
@role_required('admin')
def admin_companies():
    q=request.args.get('q','').strip()
    query=Company.query
    if q:
        query=query.filter(Company.company_name.ilike(f'%{q}%'))
    return render_template('admin/companies.html',companies=query.order_by(Company.id.desc()).all())

@app.route('/admin/companies/<int:company_id>')
@login_required
@role_required('admin')
def admin_view_company(company_id):
    company=Company.query.get_or_404(company_id)
    return render_template('admin/viewcompany.html',company=company)

@app.route('/admin/companies/<int:company_id>/approve',methods=['POST'])
@login_required
@role_required('admin')
def admin_approve_company(company_id):
    company=Company.query.get_or_404(company_id)
    company.is_approved=True
    db.session.commit()
    flash(f'Success!{company.company_name} approved!')
    return redirect(url_for('admin_companies'))
    
@app.route('/admin/companies/<int:company_id>/reject',methods=['POST'])
@login_required
@role_required('admin')
def admin_reject_company(company_id):
    company=Company.query.get_or_404(company_id)
    company.is_approved=False
    company.user.is_active=False
    db.session.commit()
    flash(f'{company.company_name} rejected!')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/<int:company_id>/blacklist',methods=['POST'])
@login_required
@role_required('admin')
def admin_blacklist_company(company_id):
    company=Company.query.get_or_404(company_id)
    company.is_blacklisted=True
    company.user.is_active=False
    for drive in company.drives:
        drive.drive_status='Closed'
        drive.approval_status='Rejected'
    db.session.commit()
    flash(f'{company.company_name} blacklisted!!')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/<int:company_id>/unblacklist',methods=['POST'])
@login_required
@role_required('admin')
def admin_unblacklist_company(company_id):
    company=Company.query.get_or_404(company_id)
    company.is_blacklisted=False
    company.user.is_active=True
    db.session.commit()
    flash(f'Success! {company.company_name} restored!!')
    return redirect(url_for('admin_companies'))

@app.route('/admin/students')
@login_required
@role_required('admin')
def admin_students():
    q=request.args.get('q','').strip()
    query=Student.query.join(User)
    if q:
        query=query.filter(db.or_(
            Student.name.ilike(f'%{q}%'),
            Student.roll_number.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%'),
            ))
    return render_template('admin/students.html',students=query.order_by(Student.id.desc()).all())

@app.route('/admin/students/<int:student_id>')
@login_required
@role_required('admin')
def admin_view_student(student_id):
    student=Student.query.get_or_404(student_id)
    return render_template('admin/view_student.html',student=student)

@app.route('/admin/students/<int:student_id>/blacklist',methods=['POST'])
@login_required
@role_required('admin')
def admin_blacklist_student(student_id):
    student=Student.query.get_or_404(student_id)
    student.is_blacklisted=True
    student.user.is_active=False
    db.session.commit()
    flash(f'{student.name} blacklisted!!')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/<int:student_id>/unblacklist',methods=['POST'])
@login_required
@role_required('admin')
def admin_unblacklist_student(student_id):
    student=Student.query.get_or_404(student_id)
    student.is_blacklisted=False
    student.user.is_active=True
    db.session.commit()
    flash(f'Success! {student.name} restored!!')
    return redirect(url_for('admin_students'))

@app.route('/admin/drives')
@login_required
@role_required('Admin')
def admin_drives():
    status = request.args.get('status', 'all')
    query  = PlacementDrive.query
    if status != 'all':
        query = query.filter_by(approval_status=status)
    return render_template('admin/drives.html',
        drives = query.order_by(PlacementDrive.id.desc()).all(),
        filter = status,
    )

@app.route('/admin/drives/<int:drive_id>')
@login_required
@role_required('Admin')
def admin_view_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    return render_template('admin/view_drive.html', drive=drive)


@app.route('/admin/drives/<int:drive_id>/approve', methods=['POST'])
@login_required
@role_required('Admin')
def admin_approve_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.approval_status = 'Approved'
    db.session.commit()
    flash(f'Success! Drive "{drive.title}" approved.')
    return redirect(url_for('admin_drives'))

@app.route('/admin/drives/<int:drive_id>/reject', methods=['POST'])
@login_required
@role_required('Admin')
def admin_reject_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.approval_status = 'Rejected'
    db.session.commit()
    flash(f'Drive "{drive.title}" rejected.')
    return redirect(url_for('admin_drives'))

@app.route('/admin/applications/<int:app_id>')
@login_required
@role_required('Admin')
def admin_view_application(app_id):
    application = Application.query.get_or_404(app_id)
    return render_template('admin/view_application.html', application=application)

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