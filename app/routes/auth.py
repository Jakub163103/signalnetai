from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf.csrf import CSRFError
import json
import os

from app import db
from app.models import User
from app.forms import LoginForm, SignupForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import generate_reset_token, send_reset_email
from flask import current_app

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        try:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(
                email=form.email.data,
                password_hash=hashed_password,
                country=form.country.data
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! You can now log in.', 'success')
            return render_template('signup.html', form=SignupForm(), countries=form.country.choices, signup_success=True)
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while creating your account. Please try again.', 'danger')
            print(f"Database Error: {e}")
    
    countries = form.country.choices
    return render_template('signup.html', form=form, countries=countries, signup_success=False)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = generate_reset_token(user.id)
            send_reset_email(user.email, token)
            flash('A password reset link has been sent to your email.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with that email address.', 'warning')
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm()
    user_id = verify_reset_token(token)
    if user_id is None:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    user = User.query.get(user_id)
    if form.validate_on_submit():
        try:
            user.password_hash = generate_password_hash(form.password.data)
            db.session.commit()
            flash('Your password has been updated! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while updating your password. Please try again.', 'danger')
            current_app.logger.error(f"Error updating password: {e}")
    return render_template('reset_password.html', form=form)

@auth_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('The form you submitted is invalid or has expired. Please try again.', 'danger')
    return redirect(url_for('auth.signup'))

