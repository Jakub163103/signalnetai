from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user
import stripe
from app.forms import SubscribeForm, ContactForm, UpdateProfileForm, AdminNotificationForm, PrivacySettingsForm, AccountSettingsForm, CancelSubscriptionForm, QuickSignalForm
from app.models import Subscription, User, Notification, db, ContactMessage, CancellationFeedback
from app.utils import send_notification
from werkzeug.utils import secure_filename
import os
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.signal_generator import generate_signal  # Your signal generation logic

main_bp = Blueprint('main', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/')
def home():
    subscriptions = Subscription.query.all()
    form = SubscribeForm()
    return render_template(
        'index.html',
        subscriptions=subscriptions,
        form=form,
        stripe_public_key=current_app.config['STRIPE_PUBLIC_KEY']
    )
@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Handle form submission logic (e.g., store message, send email)
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('main.contact'))
    return render_template('contact.html', form=form)

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/services')
def services():
    if not current_user.is_authenticated:
        flash('Please log in to access the services.', 'warning')
        return redirect(url_for('auth.login'))
    
    services_list = [
        {
            'name': 'Quick Signal',
            'slug': 'quick-signal',
            'description': 'Our Quick Signal service provides real-time financial market signals to help you make informed decisions swiftly.'
        },
    ]
    return render_template('services.html', services=services_list)

@main_bp.route('/services/<slug>')
def service_detail(slug):
    if not current_user.is_authenticated:
        flash('Please log in to access the service details.', 'warning')
        return redirect(url_for('auth.login'))
    
    user = current_user

    # Check if the user has an active subscription
    if not user.subscription:
        flash('You need an active subscription to access this service.', 'warning')
        return redirect(url_for('main.subscribe'))

    service_details = {
        'quick-signal': {
            'name': 'Quick Signal',
            'description': 'Our Quick Signal service provides real-time financial market signals to help you make informed decisions swiftly.',
            'features': [
                'Real-time data access',
                'Customizable alerts',
                'Comprehensive market analysis'
            ]
        },
    }

    service = service_details.get(slug)
    if not service:
        return render_template('404.html'), 404

    pairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    prices = {}  # Implement logic to fetch and populate prices

    return render_template('services/quick_signal.html', service=service, pairs=pairs, prices=prices)

@main_bp.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    form = SubscribeForm()
    subscriptions = Subscription.query.all()
    stripe_public_key = current_app.config['STRIPE_PUBLIC_KEY']  # Retrieve the publishable key

    if form.validate_on_submit():
        subscription_name = form.subscription.data
        price_id_map = {
            'Basic': current_app.config['BASIC_PRICE_ID'],
            'Pro': current_app.config['PRO_PRICE_ID'],
            'Professional': current_app.config['PROFESSIONAL_PRICE_ID']
        }
        price_id = price_id_map.get(subscription_name)

        if not price_id:
            flash('Invalid subscription plan selected.', 'danger')
            return redirect(url_for('main.subscribe'))

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('main.payment_cancelled', _external=True),
                customer_email=current_user.email,
                client_reference_id=str(current_user.id)
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            flash(f'An error occurred while creating the checkout session: {str(e)}', 'danger')
            return redirect(url_for('main.subscribe'))

    return render_template('subscribe.html', subscriptions=subscriptions, form=form, stripe_public_key=stripe_public_key)

@main_bp.route('/payment_success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No session ID provided.', 'danger')
        return redirect(url_for('main.subscribe'))
    
    try:
        # Retrieve the checkout session from Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        
        # Extract the subscription plan ID from the session metadata
        subscription_plan_id = checkout_session.metadata.get('subscription_plan_id')
        
        if not subscription_plan_id:
            flash('Subscription plan ID not found.', 'danger')
            return redirect(url_for('main.subscribe'))
        
        # Retrieve the Stripe Subscription ID
        stripe_subscription_id = checkout_session.subscription
        
        if not stripe_subscription_id:
            flash('Stripe subscription ID not found.', 'danger')
            return redirect(url_for('main.subscribe'))
        
        # Update the user's subscription in the database
        current_user.subscription_id = subscription_plan_id
        current_user.stripe_subscription_id = stripe_subscription_id  # Store Stripe Subscription ID
        db.session.commit()
        
        flash('Your subscription was successful!', 'success')
        return redirect(url_for('main.success'))  # Redirect to a dashboard or relevant page
    except Exception as e:
        current_app.logger.error(f"Error retrieving Stripe session: {e}")
        flash(f'Error retrieving Stripe session: {str(e)}', 'danger')
        return redirect(url_for('main.subscribe'))

@main_bp.route('/payment_cancelled')
@login_required
def payment_cancelled():
    flash('Your payment was cancelled.', 'info')
    return redirect(url_for('main.subscribe'))

@main_bp.route('/success')
def success():
    flash('Subscription successful!', 'success')
    return redirect(url_for('main.profile'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Logic for the dashboard
    return render_template('dashboard.html')

# Added Privacy Policy Route
@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

# Added Terms of Service Route
@main_bp.route('/terms-of-service')
def terms_of_service():
    return render_template('terms.html')

# Added Cookie Policy Route
@main_bp.route('/cookie-policy')
def cookie_policy():
    return render_template('cookie_policy.html')

@main_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    form = PrivacySettingsForm()
    return render_template('notifications.html', notifications=notifications, form=form)

@main_bp.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.notifications'))
    
    notification.read = True
    db.session.commit()
    flash('Notification marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/delete_notification/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.notifications'))
    
    db.session.delete(notification)
    db.session.commit()
    flash('Notification deleted.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    notifications = Notification.query.filter_by(user_id=current_user.id, read=False).all()
    for notification in notifications:
        notification.read = True
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/delete_all_notifications', methods=['POST'])
@login_required
def delete_all_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    for notification in notifications:
        db.session.delete(notification)
    db.session.commit()
    flash('All notifications deleted.', 'success')
    return redirect(url_for('main.notifications'))

@main_bp.route('/profile')
@login_required
def profile():
    form = UpdateProfileForm()
    return render_template('profile.html', form=form)

@main_bp.route('/account_settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    form = AccountSettingsForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.password = form.password.data
        db.session.commit()
        flash('Your account settings have been updated.', 'success')
        return redirect(url_for('main.account_settings'))
    return render_template('account_settings.html', form=form)

@main_bp.route('/privacy_settings', methods=['GET', 'POST'])
@login_required
def privacy_settings():
    form = PrivacySettingsForm(obj=current_user)
    if form.validate_on_submit():
        current_user.allow_marketing_emails = form.allow_marketing_emails.data
        current_user.share_data_with_partners = form.share_data_with_partners.data
        current_user.allow_profile_visibility = form.allow_profile_visibility.data
        try:
            db.session.commit()
            flash('Your privacy settings have been updated.', 'success')
            current_app.logger.info(f"User {current_user.username} updated privacy settings.")
            return redirect(url_for('main.privacy_settings'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update privacy settings for user {current_user.username}: {e}")
            flash('Failed to update privacy settings. Please try again.', 'danger')
    return render_template('privacy_settings.html', form=form)

@main_bp.route('/help_center', methods=['GET', 'POST'])
def help_center():
    form = ContactForm()
    if form.validate_on_submit():
        # Create a new ContactMessage instance
        contact_message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data
        )
        try:
            db.session.add(contact_message)
            db.session.commit()
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('main.help_center'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while sending your message. Please try again later.', 'danger')
    
    return render_template('help_center.html', form=form)

@main_bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if 'profile_picture' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.profile'))

    file = request.files['profile_picture']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('main.profile'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        # Update user's profile picture in the database
        current_user.profile_picture = filename
        db.session.commit()
        flash('Profile picture updated successfully!', 'success')
        return redirect(url_for('main.profile'))
    
@main_bp.route('/admin/send_notification', methods=['GET', 'POST'])
@login_required
def admin_send_notification():
    form = AdminNotificationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            topic = form.topic.data
            message = form.message.data
            if not message or not topic:
                flash('Both topic and message cannot be empty', 'danger')
                return redirect(url_for('main.admin_send_notification'))

            # Assuming you want to send the notification to all users
            users = User.query.all()
            for user in users:
                full_message = f"{topic}: {message}"
                send_notification(user.id, current_user.id, full_message)

            flash('Notifications sent successfully', 'success')
            return redirect(url_for('main.admin_send_notification'))
    return render_template('admin_send_notification.html', form=form)

@main_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.password.data:
            current_user.password = form.password.data  # Utilizes the password setter
        try:
            db.session.commit()
            flash('Your profile has been updated!', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('main.profile'))

@main_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    data = request.get_json()
    subscription_name = data.get('subscription')

    if not subscription_name:
        return jsonify({'error': 'No subscription plan provided.'}), 400

    # Map subscription names to their respective Stripe Price IDs
    price_id_map = {
        'Basic': current_app.config['BASIC_PRICE_ID'],
        'Pro': current_app.config['PRO_PRICE_ID'],
        'Professional': current_app.config['PROFESSIONAL_PRICE_ID']
    }

    price_id = price_id_map.get(subscription_name)

    if not price_id:
        return jsonify({'error': 'Invalid subscription plan selected.'}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.payment_cancelled', _external=True),
            customer_email=current_user.email,
            client_reference_id=str(current_user.id),
            metadata={
                'subscription_plan_id': Subscription.query.filter_by(name=subscription_name).first().id
            }
        )
        # Optionally, store the Stripe Checkout Session ID if needed
        current_user.stripe_checkout_session_id = checkout_session.id
        db.session.commit()
        return jsonify({'id': checkout_session.id, 'url': checkout_session.url})
    except Exception as e:
        current_app.logger.error(f"Stripe Checkout Session creation failed: {e}")
        return jsonify({'error': 'An error occurred while creating the checkout session.'}), 500

@main_bp.route('/cancel_subscription', methods=['POST'])
@login_required
def cancel_subscription():
    return redirect(url_for('main.cancel_subscription_feedback'))

@main_bp.route('/cancel_subscription_feedback', methods=['GET', 'POST'])
@login_required
def cancel_subscription_feedback():
    form = CancelSubscriptionForm()
    if form.validate_on_submit():
        reason = form.reason.data
        additional_comments = form.additional_comments.data

        try:
            # Retrieve the Stripe Subscription ID from the user's record
            stripe_subscription_id = current_user.stripe_subscription_id
            if not stripe_subscription_id:
                flash('No active Stripe subscription found.', 'warning')
                return redirect(url_for('main.profile'))

            # Cancel the subscription on Stripe
            stripe.Subscription.delete(stripe_subscription_id)

            # Update the user's subscription status in the database
            current_user.subscription_id = None
            current_user.stripe_subscription_id = None
            db.session.commit()

            # Store the cancellation feedback
            feedback = CancellationFeedback(
                user_id=current_user.id,
                reason=reason,
                additional_comments=additional_comments
            )
            db.session.add(feedback)
            db.session.commit()

            flash('Your subscription has been canceled successfully.', 'success')
            return redirect(url_for('main.subscribe'))
        except Exception as e:
            current_app.logger.error(f"Error canceling subscription: {e}")
            flash('An error occurred while canceling your subscription. Please try again later.', 'danger')
            return redirect(url_for('main.profile'))

    return render_template('cancel_subscription.html', form=form)

@main_bp.route('/quick_signal', methods=['GET', 'POST'], endpoint='generate_signal')
@login_required
def generate_signal_view():
    form = QuickSignalForm()
    signal = None
    if form.validate_on_submit():
        cryptocurrency = form.cryptocurrency.data
        timeframe = form.timeframe.data
        try:
            # Call your signal generation function
            signal_result = generate_signal(cryptocurrency, timeframe)
            
            # Structure the signal data to pass to the template
            signal = {
                'cryptocurrency': cryptocurrency.capitalize(),
                'result': signal_result
            }
            flash('Signal generated successfully!', 'success')
        except Exception as e:
            # Log the error and inform the user
            current_app.logger.error(f"Error generating signal: {e}")
            flash('An error occurred while generating the signal. Please try again.', 'danger')
            signal = None
    return render_template('quick_signal.html', form=form, signal=signal)

@main_bp.route('/services/quick-signal', methods=['GET', 'POST'])
@login_required
def quick_signal():
    form = QuickSignalForm()
    signal = None
    if form.validate_on_submit():
        cryptocurrency = form.cryptocurrency.data
        timeframe = form.timeframe.data
        try:
            # Replace this with your actual signal generation logic
            signal_result = generate_signal(cryptocurrency, timeframe)

            # Structure the signal data to pass to the template
            signal = {
                'cryptocurrency': cryptocurrency.capitalize(),
                'result': signal_result
            }
            flash('Signal generated successfully!', 'success')
        except Exception as e:
            # Log the error and inform the user
            current_app.logger.error(f"Error generating signal: {e}")
            flash('An error occurred while generating the signal. Please try again.', 'danger')
            signal = None
    return render_template('services/quick_signal.html', form=form, signal=signal)