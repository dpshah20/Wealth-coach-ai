from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    clerk_user_id = db.Column(db.String(255), unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    age = db.Column(db.Integer)
    email = db.Column(db.String(255), index=True)
    password_hash = db.Column(db.String(255))
    monthly_surplus = db.Column(db.Integer)
    risk_tolerance = db.Column(db.String(50))  # low, medium, high
    investment_goals = db.Column(db.String(255))
    investment_horizon = db.Column(db.Integer)  # years
    knowledge_level = db.Column(db.String(50), default='beginner')  # beginner, intermediate, advanced
    onboarding_completed = db.Column(db.Boolean, default=False)
    last_login_at = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime)
    session_data = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    chat_messages = db.relationship('ChatMessage', backref='user', lazy=True, cascade='all, delete-orphan')
    learning_progress = db.relationship('LearningProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        try:
            parsed_session_data = json.loads(self.session_data or '{}')
        except Exception:
            parsed_session_data = {}
        return {
            'id': self.id,
            'first_name': self.first_name,
            'surname': self.surname,
            'age': self.age,
            'email': self.email,
            'monthly_surplus': self.monthly_surplus,
            'risk_tolerance': self.risk_tolerance,
            'investment_goals': self.investment_goals,
            'investment_horizon': self.investment_horizon,
            'knowledge_level': self.knowledge_level,
            'onboarding_completed': self.onboarding_completed,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'session_data': parsed_session_data,
        }

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }

class LearningProgress(db.Model):
    __tablename__ = 'learning_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)  # topic name
    status = db.Column(db.String(50), default='not_started')  # not_started, in_progress, completed
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'topic': self.topic,
            'status': self.status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
