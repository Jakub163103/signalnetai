from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, HiddenField, SelectField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError, NumberRange
from flask_login import current_user
from app.models import User
import json
import os
from app.utils import load_countries

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Username is required."),
        Length(min=3, max=150, message='Username must be between 3 and 150 characters.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Username is required."),
        Length(min=3, max=150, message='Username must be between 3 and 150 characters.')
    ])
    email = StringField('Email', validators=[
        DataRequired(message="Email is required."),
        Email(message="Invalid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    country = SelectField('Country', choices=[], validators=[DataRequired()])
    tos = BooleanField('I accept the Terms of Service', validators=[
        DataRequired(message="You must accept the Terms of Service.")
    ])
    submit = SubmitField('Sign Up')

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        # Determine the absolute path to countries.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        countries_file = os.path.join(current_dir, 'static', 'data', 'countries.json')
        
        # Load countries from the JSON file
        try:
            with open(countries_file, 'r', encoding='utf-8') as f:
                countries = json.load(f)
            # Populate the country choices as (code, name) tuples
            self.country.choices = [(country['code'], country['name']) for country in countries]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Handle errors gracefully
            self.country.choices = []
            print(f"Error loading countries: {e}")

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('That email is already in use. Please choose a different one.')

class SubscribeForm(FlaskForm):
    subscription = HiddenField('Subscription Plan', validators=[
        DataRequired(message="Please select a subscription plan.")
    ])
    submit = SubmitField('Subscribe')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Update Password')

class UpdateProfileForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Username is required."),
        Length(min=3, max=150, message='Username must be between 3 and 150 characters.')
    ])
    email = StringField('Email', validators=[
        DataRequired(message="Email is required."),
        Email(message="Invalid email address.")
    ])
    password = PasswordField('New Password (leave blank to keep current password)', validators=[
        Optional(),
        Length(min=6, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        EqualTo('password', message="Passwords must match."),
        Optional()
    ])
    submit = SubmitField('Update Profile')

class AccountSettingsForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('New Password (leave blank to keep current password)', validators=[
        Optional(),
        Length(min=6, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        EqualTo('password', message="Passwords must match."),
        Optional()
    ])
    submit = SubmitField('Update Account')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already in use. Please choose a different one.')

class PrivacySettingsForm(FlaskForm):
    # Notification Preferences
    email_notifications = BooleanField('Email Notifications')
    sms_notifications = BooleanField('SMS Notifications')
    in_app_notifications = BooleanField('In-App Notifications')
    
    # Privacy Settings
    allow_marketing_emails = BooleanField('Allow Marketing Emails')
    share_data_with_partners = BooleanField('Share Data with Partners')
    allow_profile_visibility = BooleanField('Allow Profile Visibility')
    
    submit = SubmitField('Save Preferences')

    def validate_email_notifications(self, field):
        pass

    def validate_sms_notifications(self, field):
        pass

    def validate_in_app_notifications(self, field):
        pass

    def validate_allow_marketing_emails(self, field):
        pass

    def validate_share_data_with_partners(self, field):
        pass

    def validate_allow_profile_visibility(self, field):
        pass

class AdminNotificationForm(FlaskForm):
    topic = StringField('Notification Topic', validators=[DataRequired(), Length(max=100)])
    message = TextAreaField('Notification Message', validators=[DataRequired()])
    submit = SubmitField('Send Notification')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=100)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Send Message')

class EditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    country = SelectField('Country', choices=[], validators=[DataRequired()])
    is_admin = BooleanField('Admin')
    submit = SubmitField('Update')

    def __init__(self, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        # Populate the country choices from the countries.json file
        self.country.choices = [(country['code'], country['name']) for country in load_countries()]

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')

class ApplicationSettingsForm(FlaskForm):
    site_title = StringField('Site Title', validators=[DataRequired(), Length(max=100)])
    maintenance_mode = BooleanField('Enable Maintenance Mode')
    default_user_role = StringField('Default User Role', validators=[DataRequired(), Length(max=50)])
    logs_display_count = IntegerField('Number of Logs to Display', validators=[DataRequired(), NumberRange(min=1, max=100)])
    submit = SubmitField('Save Settings')

class CancelSubscriptionForm(FlaskForm):
    reason = SelectField(
        'Why are you canceling your subscription?',
        choices=[
            ('pricing', 'Too Expensive'),
            ('features', 'Missing Features'),
            ('usage', 'Not Using It Enough'),
            ('other', 'Other')
        ],
        validators=[DataRequired()]
    )
    additional_comments = TextAreaField('Additional Comments (optional)')
    submit = SubmitField('Submit')

class QuickSignalForm(FlaskForm):
    cryptocurrency = SelectField(
        'Cryptocurrency',
        choices=[
            ('bitcoin', 'Bitcoin (BTC)'),
            ('ethereum', 'Ethereum (ETH)'),
            ('litecoin', 'Litecoin (LTC)'),
            ('ripple', 'Ripple (XRP)'),
            ('cardano', 'Cardano (ADA)'),
            # Add more cryptocurrencies as needed
        ],
        validators=[DataRequired()]
    )
    timeframe = SelectField(
        'Timeframe',
        choices=[
            ('1h', '1 Hour'),
            ('4h', '4 Hours'),
            ('1d', '1 Day'),
            # Add more timeframes as needed
        ],
        validators=[DataRequired()]
    )
    submit = SubmitField('Generate Signal')