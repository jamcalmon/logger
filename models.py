from init import app, db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    pw_hash = db.Column(db.String(50))

class Activity(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    description = db.Column(db.String(128))
    start_time = db.Column(db.DateTime, default=datetime.utcnow())
    end_time = db.Column(db.DateTime, default=datetime.utcnow())
    current = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref = "activities")

db.create_all(app=app)