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
    return render_template('admin/view_company.html',company=company)

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
@role_required('admin')
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
@role_required('admin')
def admin_view_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    return render_template('admin/view_drive.html', drive=drive)


@app.route('/admin/drives/<int:drive_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def admin_approve_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.approval_status = 'Approved'
    db.session.commit()
    flash(f'Success! Drive "{drive.title}" approved.')
    return redirect(url_for('admin_drives'))

@app.route('/admin/drives/<int:drive_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def admin_reject_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.approval_status = 'Rejected'
    db.session.commit()
    flash(f'Drive "{drive.title}" rejected.')
    return redirect(url_for('admin_drives'))

@app.route('/admin/applications/<int:app_id>')
@login_required
@role_required('admin')
def admin_view_application(app_id):
    application = Application.query.get_or_404(app_id)
    return render_template('admin/view_application.html', application=application)

@app.route('/company/dashboard')
@login_required
@role_required('company')
def company_dashboard():
    company = current_user.company
    return render_template('company/dashboard.html',
        company            = company,
        upcoming_drives    = PlacementDrive.query.filter_by(company_id=company.id, drive_status='Open').all(),
        closed_drives      = PlacementDrive.query.filter_by(company_id=company.id, drive_status='Closed').all(),
        total_drives       = PlacementDrive.query.filter_by(company_id=company.id).count(),
        total_applications = Application.query.join(PlacementDrive).filter(PlacementDrive.company_id == company.id).count(),
        shortlisted        = Application.query.join(PlacementDrive).filter(PlacementDrive.company_id == company.id, Application.application_status == 'Shortlisted').count(),
        selected           = Application.query.join(PlacementDrive).filter(PlacementDrive.company_id == company.id, Application.application_status == 'Selected').count(),
    )

@app.route('/company/drives')
@login_required
@role_required('company')
def company_drives():
    company = current_user.company
    return render_template('company/drives.html',
        drives = PlacementDrive.query.filter_by(company_id=company.id).order_by(PlacementDrive.created_at.desc()).all()
    )

@app.route('/company/drives/create', methods=['GET', 'POST'])
@login_required
@role_required('company')
def company_create_drive():
    if request.method == 'POST':
        from datetime import datetime
        company  = current_user.company
        title    = request.form.get('title', '').strip()
        job_role = request.form.get('job_role', '').strip()
        if not title or not job_role:
            flash('Drive name and job role are required.')
            return render_template('company/create_drive.html')
        deadline_str   = request.form.get('application_deadline', '')
        drive_date_str = request.form.get('drive_date', '')
        drive = PlacementDrive(
            company_id           = company.id,
            title                = title,
            job_role             = job_role,
            description          = request.form.get('description', '').strip(),
            package              = float(request.form.get('package')) if request.form.get('package') else None,
            eligibility_cgpa     = float(request.form.get('eligibility_cgpa')) if request.form.get('eligibility_cgpa') else None,
            eligibility_criteria = request.form.get('eligibility_criteria', '').strip(),
            application_deadline = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None,
            drive_date           = datetime.strptime(drive_date_str, '%Y-%m-%d') if drive_date_str else None,
        )
        db.session.add(drive)
        db.session.commit()
        flash('Drive submitted for admin approval.')
        return redirect(url_for('company_dashboard'))
    return render_template('company/create_drive.html')

@app.route('/company/drives/<int:drive_id>')
@login_required
@role_required('company')
def company_view_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        abort(403)
    return render_template('company/view_drive.html', drive=drive)

@app.route('/company/drives/<int:drive_id>/close', methods=['POST'])
@login_required
@role_required('company')
def company_close_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        abort(403)
    drive.drive_status = 'Closed'
    db.session.commit()
    flash('Drive closed.')
    return redirect(url_for('company_view_drive', drive_id=drive_id))

@app.route('/company/drives/<int:drive_id>/save-statuses', methods=['POST'])
@login_required
@role_required('company')
def company_save_statuses(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        abort(403)
    for application in drive.applications:
        new_status = request.form.get(f'status_{application.id}')
        if new_status in ('Applied', 'Shortlisted', 'Interview', 'Selected', 'Rejected'):
            application.application_status = new_status
    db.session.commit()
    flash('Success! Statuses updated.')
    return redirect(url_for('company_view_drive', drive_id=drive_id))

@app.route('/company/applications/<int:app_id>')
@login_required
@role_required('company')
def company_view_application(app_id):
    application = Application.query.get_or_404(app_id)
    if application.drive.company_id != current_user.company.id:
        abort(403)
    return render_template('company/view_application.html', application=application)

@app.route('/company/applications/<int:app_id>/update', methods=['POST'])
@login_required
@role_required('company')
def company_update_application(app_id):
    application = Application.query.get_or_404(app_id)
    if application.drive.company_id != current_user.company.id:
        abort(403)
    new_status = request.form.get('status')
    if new_status in ('Applied', 'Shortlisted', 'Interview', 'Selected', 'Rejected'):
        application.application_status = new_status
    application.remark = request.form.get('remark', '').strip()
    db.session.commit()
    flash('Success! Application updated.')
    return redirect(url_for('company_view_application', app_id=app_id))

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    student = current_user.student
    return render_template('student/dashboard.html',
        student          = student,
        applied_drives   = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all(),
        active_companies = Company.query.filter_by(is_approved=True, is_blacklisted=False).all(),
    )

@app.route('/student/drives')
@login_required
@role_required('student')
def student_drives():
    q     = request.args.get('q', '').strip()
    query = PlacementDrive.query.filter_by(approval_status='Approved', drive_status='Open')
    if q:
        query = query.join(Company).filter(db.or_(
            PlacementDrive.title.ilike(f'%{q}%'),
            PlacementDrive.job_role.ilike(f'%{q}%'),
            Company.company_name.ilike(f'%{q}%'),
        ))
    student           = current_user.student
    applied_drive_ids = {a.drive_id for a in student.applications}
    return render_template('student/drives.html',
        drives            = query.order_by(PlacementDrive.created_at.desc()).all(),
        applied_drive_ids = applied_drive_ids,
    )

@app.route('/student/drives/<int:drive_id>')
@login_required
@role_required('student')
def student_view_drive(drive_id):
    drive   = PlacementDrive.query.get_or_404(drive_id)
    student = current_user.student
    if drive.approval_status != 'Approved':
        abort(404)
    already_applied   = Application.query.filter_by(student_id=student.id, drive_id=drive_id).first() is not None
    can_apply         = True
    ineligible_reason = ''
    if student.is_blacklisted:
        can_apply = False
        ineligible_reason = 'Your account has been blacklisted.'
    elif drive.drive_status != 'Open':
        can_apply = False
        ineligible_reason = 'This drive is no longer accepting applications.'
    elif drive.eligibility_cgpa and (student.cgpa or 0) < drive.eligibility_cgpa:
        can_apply = False
        ineligible_reason = f'This drive requires a minimum CGPA of {drive.eligibility_cgpa}.'
    return render_template('student/view_drive.html',
        drive=drive, already_applied=already_applied,
        can_apply=can_apply, ineligible_reason=ineligible_reason,
    )

@app.route('/student/drives/<int:drive_id>/apply', methods=['POST'])
@login_required
@role_required('student')
def student_apply(drive_id):
    student = current_user.student
    drive   = PlacementDrive.query.get_or_404(drive_id)
    if drive.approval_status != 'Approved' or drive.drive_status != 'Open':
        flash('This drive is not open for applications.')
        return redirect(url_for('student_view_drive', drive_id=drive_id))
    if student.is_blacklisted:
        flash('Your account has been blacklisted.')
        return redirect(url_for('student_view_drive', drive_id=drive_id))
    if drive.eligibility_cgpa and (student.cgpa or 0) < drive.eligibility_cgpa:
        flash('You do not meet the CGPA requirement.')
        return redirect(url_for('student_view_drive', drive_id=drive_id))
    if Application.query.filter_by(student_id=student.id, drive_id=drive_id).first():
        flash('You have already applied for this drive.')
        return redirect(url_for('student_view_drive', drive_id=drive_id))
    db.session.add(Application(student_id=student.id, drive_id=drive_id))
    db.session.commit()
    flash(f'Success! Applied for {drive.title}.')
    return redirect(url_for('student_applications'))

@app.route('/student/applications')
@login_required
@role_required('student')
def student_applications():
    student = current_user.student
    return render_template('student/applications.html',
        student      = student,
        applications = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all(),
    )

@app.route('/student/applications/<int:app_id>')
@login_required
@role_required('student')
def student_view_application(app_id):
    application = Application.query.get_or_404(app_id)
    if application.student_id != current_user.student.id:
        abort(403)
    return render_template('student/view_application.html', application=application)

@app.route('/student/company/<int:company_id>')
@login_required
@role_required('student')
def student_company_detail(company_id):
    company = Company.query.get_or_404(company_id)
    drives  = PlacementDrive.query.filter_by(company_id=company_id, approval_status='Approved', drive_status='Open').all()
    return render_template('student/company_detail.html', company=company, drives=drives)

@app.route('/student/profile/edit', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_edit_profile():
    student = current_user.student
    if request.method == 'POST':
        student.name       = request.form.get('name', '').strip()
        student.department = request.form.get('department', '')
        cgpa               = request.form.get('cgpa', '')
        student.cgpa       = float(cgpa) if cgpa else None
        student.skills     = request.form.get('skills', '').strip()
        resume = request.files.get('resume')
        if resume and file_allowed(resume.filename):
            filename = secure_filename(f"{student.roll_number}.pdf")
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            resume.save(os.path.join(Config.UPLOAD_FOLDER, filename))
            student.resume_filename = filename
        db.session.commit()
        flash('Success! Profile updated.')
        return redirect(url_for('student_dashboard'))
    return render_template('student/edit_profile.html', student=student)

@app.route('/student/resume/<int:student_id>')
@login_required
def student_download_resume(student_id):
    student = Student.query.get_or_404(student_id)
    if current_user.role == 'student' and current_user.student.id != student_id:
        abort(403)
    if not student.resume_filename:
        abort(404)
    return send_from_directory(Config.UPLOAD_FOLDER, student.resume_filename, as_attachment=False)

@app.route('/admin/stats')
@login_required
@role_required('admin')
def admin_stats():
    from sqlalchemy import func
    total_students  = Student.query.count()
    placed_students = db.session.query(func.count(Application.student_id.distinct()))\
                       .filter(Application.application_status == 'Selected').scalar()
    drives_closed   = PlacementDrive.query.filter_by(drive_status='Closed').count()
    drives_open     = PlacementDrive.query.filter_by(drive_status='Open', approval_status='Approved').count()
    company_stats   = db.session.query(
        Company.company_name,
        func.count(Application.id).label('total'),
        func.sum(db.case((Application.application_status == 'Selected', 1), else_=0)).label('selected')
    ).join(PlacementDrive, PlacementDrive.company_id == Company.id)\
     .join(Application, Application.drive_id == PlacementDrive.id)\
     .group_by(Company.id).all()
    return render_template('admin/stats.html',
        total_students  = total_students,
        placed_students = placed_students,
        drives_closed   = drives_closed,
        drives_open     = drives_open,
        company_stats   = company_stats,
    )