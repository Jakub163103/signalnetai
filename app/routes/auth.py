from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import User
from app.forms import LoginForm, SignupForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import send_notification, generate_reset_token, send_reset_email
from flask import current_app

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        password = form.password.data
        country_code = form.country.data.strip()

        # Check if the user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash('Username or email already exists. Please try again.', 'danger')
            return redirect(url_for('auth.signup'))

        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create a new user instance
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            country=country_code
        )
        db.session.add(new_user)

        try:
            db.session.commit()
            login_user(new_user)
            send_notification(
                new_user.id,
                4,
                "Welcome to SignalNet! We're excited to have you on board."
            )
            flash('Your account has been created and you are now logged in!', 'success')
            return redirect(url_for('main.home'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while saving to the database.', 'danger')
            current_app.logger.error(f"Database error during signup: {e}")

    elif form.is_submitted():
        for field, errors in form.errors.items():
            for error in errors:
                field_label = getattr(form, field).label.text
                flash(f"Error in {field_label}: {error}", 'danger')

    return render_template('signup.html', form=form)
    
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_reset_token(user.id)
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            send_reset_email(user, reset_link)
            flash('A password reset link has been sent to your email.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Email address not found.', 'danger')
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = verify_reset_token(token)
    if not user:
        flash('That is an invalid or expired token.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user.password = hashed_password
        try:
            db.session.commit()
            flash('Your password has been updated! You are now able to log in.', 'success')
            return redirect(url_for('auth.login'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while updating your password.', 'danger')
            current_app.logger.error(f"Database error during password reset: {e}")
    return render_template('reset_password.html', form=form)

