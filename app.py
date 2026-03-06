from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from models import db,User,Student,Company
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()
    admin = User.query.filter_by(email='admin@portal.com').first()
    if not admin:
        admin = User(email='admin@portal.com', password='Admin@123', role='Admin')
        db.session.add(admin)
        db.session.commit()

import auth_routes
import admin_routes
import student_routes
import company_routes

@app.route("/")
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
