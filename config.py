#from app import app
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY=os.getenv('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI')