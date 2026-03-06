from functools import wraps
from flask import session, redirect, url_for, flash
from models import User

def role_required(role):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                flash("Please login first")
                return redirect(url_for("login_page"))

            user = User.query.get(session["user_id"])

            if user.role != role:
                flash("Access denied")
                return redirect(url_for("index"))

            return func(*args, **kwargs)

        return wrapper

    return decorator