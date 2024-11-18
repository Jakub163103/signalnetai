from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
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
    
    stripe_subscription_id = db.Column(db.String(255), nullable=True)

    cancellation_feedbacks = db.relationship(
        'CancellationFeedback',
        back_populates='user',
        lazy=True,
        cascade="all, delete",
        passive_deletes=True
    )

    one_time_purchases = db.relationship('OneTimePurchase', back_populates='user', lazy=True)

    # Prevent reading the password attribute
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')

    # Setter for password
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    # Method to verify password
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # Alias for verify_password
    def check_password(self, password):
        return self.verify_password(password)

    def __repr__(self):
        return f"<User {self.email}>"

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

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Define other fields as necessary

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
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    reason = db.Column(db.String(50), nullable=False)
    additional_comments = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='cancellation_feedbacks')

    def __repr__(self):
        return f"<CancellationFeedback {self.id} for User {self.user_id}>"

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    cost_per_signal = db.Column(db.Float, nullable=False)  # Dynamic cost per signal

    one_time_purchases = db.relationship('OneTimePurchase', back_populates='model', lazy=True)

    def __repr__(self):
        return f"<Model {self.name}>"

class OneTimePlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    signals = db.Column(db.Integer, nullable=False)

    purchases = db.relationship('OneTimePurchase', back_populates='plan', lazy=True)

    def __repr__(self):
        return f"<OneTimePlan {self.name}>"

class OneTimePurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )
    plan_id = db.Column(
        db.Integer,
        db.ForeignKey('one_time_plan.id'),
        nullable=False
    )
    model_id = db.Column(
        db.Integer,
        db.ForeignKey('model.id'),
        nullable=False
    )
    signals_purchased = db.Column(db.Integer, nullable=False)
    signals_remaining = db.Column(db.Integer, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='one_time_purchases')
    plan = db.relationship('OneTimePlan', back_populates='purchases')
    model = db.relationship('Model', back_populates='one_time_purchases')

    def __repr__(self):
        return f"<OneTimePurchase {self.id} - User {self.user_id} - Plan {self.plan_id} - Model {self.model_id}>"

