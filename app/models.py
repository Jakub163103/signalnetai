from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    subscription = db.relationship('Subscription', backref='users')
    profile_picture = db.Column(db.String(150), nullable=True)
    last_signal_reset = db.Column(db.DateTime, nullable=True)
    signals_used = db.Column(db.Integer, default=0)
    country = db.Column(db.String(2), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), nullable=False, default='User')
    
    # Privacy settings fields
    allow_marketing_emails = db.Column(db.Boolean, default=False)
    share_data_with_partners = db.Column(db.Boolean, default=False)
    allow_profile_visibility = db.Column(db.Boolean, default=True)
    
    # Relationships
    notifications = db.relationship(
        'Notification',
        foreign_keys='Notification.user_id',
        back_populates='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    sent_notifications = db.relationship(
        'Notification',
        foreign_keys='Notification.sender_id',
        back_populates='sender',
        lazy='dynamic'
    )
    stripe_subscription_id = db.Column(db.String(255), nullable=True)

    # Prevent reading the password attribute
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')

    # Setter for password
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    # Method to verify password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

    def is_admin_user(self):
        return self.is_admin

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    stripe_price_id = db.Column(db.String(50), nullable=False, unique=True)
    features = db.Column(db.Text, nullable=False)
    signals_per_day = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Subscription {self.name}>"

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Recipient
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Sender
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)

    # Relationships
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='notifications'
    )
    sender = db.relationship(
        'User',
        foreign_keys=[sender_id],
        back_populates='sent_notifications'
    )

    def __repr__(self):
        return f"<Notification {self.id} from User {self.sender_id} to User {self.user_id}>"

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    level = db.Column(db.String(50), nullable=False)  # e.g., INFO, WARNING, ERROR
    message = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('logs', lazy=True))

    def __repr__(self):
        return f'<Log {self.level}: {self.message[:20]}...>'

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)

    @staticmethod
    def get(key, default=None):
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            return setting.value
        return default

    @staticmethod
    def set(key, value):
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)

class ContactMessage(db.Model):
    __tablename__ = 'contact_message'  # Optional: Specify table name

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ContactMessage {self.subject} from {self.email}>"

class CancellationFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.String(50), nullable=False)
    additional_comments = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('cancellation_feedbacks', lazy=True))