from app.models import db, Notification
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from flask_mail import Message
from app import mail
from flask_login import current_user
import os
import json

def send_notification(recipient_id, sender_id, message):
    print(f"Attempting to send notification from {sender_id} to {recipient_id}.")  # Debugging
    notification = Notification(user_id=recipient_id, sender_id=sender_id, message=message)
    db.session.add(notification)
    try:
        db.session.commit()
        print(f"Notification sent from user {sender_id} to user {recipient_id}: {message}")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to send notification: {e}") 

def generate_reset_token(user_id, expires_sec=1800):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(user_id, salt='password-reset-salt') 

def send_reset_email(user, reset_link):
    msg = Message('Password Reset Request',
                  sender='noreply@signalnet.com',
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{reset_link}

If you did not make this request, simply ignore this email.
'''
    mail.send(msg) 

def get_unread_notifications_count():
    if current_user.is_authenticated:
        from app.models import Notification  # Delayed import
        return Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return 0 

def load_countries():
    """
    Loads the list of countries from the JSON file.

    Returns:
        list: A list of dictionaries containing country codes, names, and flag URLs.
    """
    countries_file = os.path.join(current_app.root_path, 'static', 'data', 'countries.json')
    try:
        with open(countries_file, 'r', encoding='utf-8') as f:
            countries = json.load(f)
        return countries
    except FileNotFoundError:
        current_app.logger.error(f"Countries file not found at {countries_file}.")
        return []
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from {countries_file}: {e}")
        return [] 