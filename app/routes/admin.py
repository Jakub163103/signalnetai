from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user

from app.forms import AdminNotificationForm, EditUserForm, DeleteForm, ApplicationSettingsForm
from app.models import User, Log, Setting
from app.utils import send_notification, load_countries
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app
from app import db  # Ensure you have access to the database instance
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/send_notification', methods=['GET', 'POST'])
@login_required
def send_notification_route():
    form = AdminNotificationForm()
    if form.validate_on_submit():
        topic = form.topic.data
        message = form.message.data
        if not message or not topic:
            flash('Both topic and message cannot be empty', 'danger')
            return redirect(url_for('admin.send_notification_route'))

        try:
            users = User.query.all()
            for user in users:
                full_message = f"{topic}: {message}"
                send_notification(user.id, current_user.id, full_message)
            flash('Notifications sent successfully', 'success')
            return redirect(url_for('admin.send_notification_route'))
        except SQLAlchemyError as e:
            flash('An error occurred while sending notifications.', 'danger')
            current_app.logger.error(f"Error sending notifications: {e}")

    return render_template('admin_send_notification.html', form=form)

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('admin_dashboard.html')

@admin_bp.route('/manage_users', methods=['GET'])
def manage_users():
    query = request.args.get('query', '').strip()
    if query:
        users = User.query.filter(
            (User.username.ilike(f'%{query}%')) | 
            (User.email.ilike(f'%{query}%'))
        ).all()
    else:
        users = User.query.all()
    form = DeleteForm()
    return render_template('manage_users.html', users=users, form=form)

@admin_bp.route('/search_users', methods=['GET'])
@login_required
def search_users():
    query = request.args.get('query', '').strip()
    if query:
        users = User.query.filter(
            (User.username.ilike(f'%{query}%')) | 
            (User.email.ilike(f'%{query}%'))
        ).all()
    else:
        users = User.query.all()
    form = DeleteForm()
    return render_template('partials/user_table_rows.html', users=users, form=form)

@admin_bp.route('/view_logs')
@login_required
def view_logs():
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    
    query = request.args.get('query', '', type=str)
    
    if query:
        logs = Log.query.filter(
            (Log.message.ilike(f'%{query}%')) |
            (Log.level.ilike(f'%{query}%'))
        ).order_by(Log.timestamp.desc()).all()
    else:
        logs = Log.query.order_by(Log.timestamp.desc()).all()
    
    return render_template('view_logs.html', logs=logs)

@admin_bp.route('/search_logs')
@login_required
def search_logs():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    query = request.args.get('query', '', type=str)
    
    if query:
        logs = Log.query.filter(
            (Log.message.ilike(f'%{query}%')) |
            (Log.level.ilike(f'%{query}%'))
        ).order_by(Log.timestamp.desc()).all()
    else:
        logs = Log.query.order_by(Log.timestamp.desc()).all()
    
    return render_template('partials/log_table_rows.html', logs=logs)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    
    form = ApplicationSettingsForm()
    
    if form.validate_on_submit():
        # Example: Update settings in the database
        Setting.set('site_title', form.site_title.data)
        Setting.set('maintenance_mode', form.maintenance_mode.data)
        Setting.set('default_user_role', form.default_user_role.data)
        Setting.set('logs_display_count', form.logs_display_count.data)
        
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))
    
    # Pre-populate form fields with existing settings
    if not form.is_submitted():
        form.site_title.data = Setting.get('site_title', 'SignalNet')
        form.maintenance_mode.data = Setting.get('maintenance_mode', False)
        form.default_user_role.data = Setting.get('default_user_role', 'User')
        form.logs_display_count.data = Setting.get('logs_display_count', 50)
    
    return render_template('application_settings.html', form=form)

@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    
    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)  # Populate form with user data

    if form.validate_on_submit():
        selected_country = form.country.data
        country_codes = [country['code'] for country in load_countries()]
        if selected_country not in country_codes:
            flash('Invalid country selected.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))
        
        user.username = form.username.data
        user.email = form.email.data
        user.country = form.country.data  # Save the selected country code
        user.is_admin = form.is_admin.data

        try:
            db.session.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating user: {e}', 'danger')
            current_app.logger.error(f"Error updating user {user_id}: {e}")

    countries = load_countries()  # Load countries data
    return render_template('edit_user.html', form=form, user=user, countries=countries)

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash('Invalid form submission.', 'danger')
        return redirect(url_for('admin.manage_users'))

    # Check if the current user has admin privileges
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    
    # Prevent admins from deleting themselves
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    # Fetch the user to be deleted
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('An error occurred while deleting the user.', 'danger')
        current_app.logger.error(f"Error deleting user {user_id}: {e}")
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/view_log/<int:log_id>')
@login_required
def view_log_detail(log_id):
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    
    log = Log.query.get_or_404(log_id)
    return render_template('view_log_detail.html', log=log)

@admin_bp.route('/delete_log/<int:log_id>', methods=['POST'])
@login_required
def delete_log(log_id):
    if not current_user.is_admin:
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('main.home'))
    
    log = Log.query.get_or_404(log_id)
    try:
        db.session.delete(log)
        db.session.commit()
        flash('Log deleted successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting log: {e}', 'danger')
        current_app.logger.error(f"Error deleting log {log_id}: {e}")
    
    return redirect(url_for('admin.view_logs'))