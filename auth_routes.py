from flask import request, redirect, session, flash, render_template
from models import User
from app import app

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email=request.form["email"]
        password=request.form["password"]
        user=User.query.filter_bt(email=email).first()

        if user and user.password == password:
            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "Admin":
                return redirect("/admin/dashboard")
            
            elif user.role == "Student":
                return redirect("/student/dashboard")
            
            elif user.role == "Company":
                return redirect("/company/dashboard")
        
        flash("Invalid credentials")

    return render_template("login.html")