from flask import Flask
from config import Config
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from models import db

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

from routes import *

def _admin_seed():
    from models import User
    if not User.query.filter_by(role='admin').first():
        admin = User(
            email='admin@portal.com',
            password=bcrypt.generate_password_hash('Admin@123').decode('utf-8'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin seeded: admin@portal.com / Admin@123")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        _admin_seed()
    app.run(debug=True, use_reloader=False)