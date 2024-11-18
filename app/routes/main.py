from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user
import stripe
from app.forms import SubscribeForm, OneTimePurchaseForm, ContactForm, UpdateProfileForm, PrivacySettingsForm, AccountSettingsForm, CancelSubscriptionForm, QuickSignalForm
from app.models import Subscription, User, OneTimePlan, OneTimePurchase, db, ContactMessage, CancellationFeedback, Model
from werkzeug.utils import secure_filename
import os
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
import logging
from app.signal_generator import generate_signal  # Your signal generation logic
import json
from sqlalchemy import desc

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
@login_required
def service_detail(slug):
    form = QuickSignalForm()
    services_list = [
        {
            'name': 'Quick Signal',
            'slug': 'quick-signal',
            'description': 'Our Quick Signal service provides real-time financial market signals to help you make informed decisions swiftly.',
            'features': ['Real-time updates', 'Comprehensive analysis', 'User-friendly interface']
        }
    ]

    service = next((s for s in services_list if s['slug'] == slug), None)
    if not service:
        flash('Service not found.', 'danger')
        return redirect(url_for('main.services'))

    has_subscription = current_user.subscription is not None
    has_one_time_purchases = OneTimePurchase.query.filter_by(user_id=current_user.id).filter(OneTimePurchase.signals_remaining > 0).count() > 0

    if not has_subscription and not has_one_time_purchases:
        flash('You need an active subscription or a valid one-time purchase to view service details.', 'warning')
        return redirect(url_for('main.subscribe'))

    return render_template('services/quick_signal.html', service=service, has_subscription=has_subscription, has_one_time_purchases=has_one_time_purchases, form=form)

@main_bp.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    form = SubscribeForm()
    one_time_purchase_form = OneTimePurchaseForm()
    subscriptions = Subscription.query.all()
    stripe_public_key = current_app.config['STRIPE_PUBLIC_KEY']

    one_time_plans = [
        {
            'id': 1,
            'name': 'Starter Pack',
            'base_price': 15.00,
            'signals': 10,
            'models': Model.query.all()
        },
        {
            'id': 2,
            'name': 'Growth Pack',
            'base_price': 60.00,
            'signals': 50,
            'models': Model.query.all()
        },
        {
            'id': 3,
            'name': 'Advanced Pack',
            'base_price': 120.00,
            'signals': 100,
            'models': Model.query.all()
        },
        {
            'id': 4,
            'name': 'Premium Pack',
            'base_price': 220.00,
            'signals': 200,
            'models': Model.query.all()
        }
    ]

    if form.validate_on_submit():
        subscription_name = form.subscription.data
        subscription = Subscription.query.filter_by(name=subscription_name).first()

        if not subscription:
            flash('Invalid subscription plan selected.', 'danger')
            return redirect(url_for('main.subscribe'))

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': subscription.stripe_price_id,
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

    return render_template(
        'subscribe.html',
        subscriptions=subscriptions,
        form=form,
        one_time_purchase_form=one_time_purchase_form,
        one_time_plans=one_time_plans,
        stripe_public_key=stripe_public_key
    )

@main_bp.route('/payment_success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No session ID provided.', 'danger')
        return redirect(url_for('main.subscribe'))

    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        # Check if this is a subscription purchase
        subscription_plan_id = session.metadata.get('subscription_plan_id')
        if subscription_plan_id:
            # Update the user's subscription
            subscription = Subscription.query.get(subscription_plan_id)
            if subscription:
                current_user.subscription_id = subscription.id
                current_user.stripe_subscription_id = session.subscription
                db.session.commit()
                flash('Subscription updated successfully!', 'success')
            else:
                flash('Invalid subscription plan.', 'danger')
        else:
            # Handle one-time purchases as before
            selected_models_json = session.metadata.get('selected_models', '{}')
            selected_models = json.loads(selected_models_json)

            one_time_purchases = []
            for plan_id_str, model_id in selected_models.items():
                plan = OneTimePlan.query.get(plan_id_str)
                if not plan:
                    current_app.logger.error(f"Plan ID {plan_id_str} not found.")
                    continue

                model = Model.query.get(model_id)
                if not model:
                    current_app.logger.error(f"Model ID {model_id} not found.")
                    continue

                purchase = OneTimePurchase(
                    user_id=current_user.id,
                    plan_id=plan.id,
                    model_id=model.id,
                    signals_purchased=plan.signals,
                    signals_remaining=plan.signals
                )
                one_time_purchases.append(purchase)
                db.session.add(purchase)

            if one_time_purchases:
                db.session.commit()
                flash('Purchase successful!', 'success')
            else:
                flash('No valid purchases were recorded.', 'warning')

    except Exception as e:
        current_app.logger.error(f"Error processing payment success: {e}")
        flash('An error occurred while processing your purchase.', 'danger')

    return redirect(url_for('main.profile'))

@main_bp.route('/payment_cancelled')
@login_required
def payment_cancelled():
    flash('Your payment was cancelled.', 'info')
    return redirect(url_for('main.subscribe'))

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

@main_bp.route('/profile')
@login_required
def profile():
    form = UpdateProfileForm()
    one_time_purchases = OneTimePurchase.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', form=form, one_time_purchases=one_time_purchases)

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
    
@main_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
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

    # Query the Subscription model to get the plan details
    subscription = Subscription.query.filter_by(name=subscription_name).first()

    if not subscription:
        return jsonify({'error': 'Invalid subscription plan selected.'}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': subscription.stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.payment_cancelled', _external=True),
            customer_email=current_user.email,
            client_reference_id=str(current_user.id),
            metadata={
                'subscription_plan_id': subscription.id
            }
        )
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

@main_bp.route('/quick_signal', methods=['GET', 'POST'])
@login_required
def quick_signal():
    # Retrieve the user's subscription
    subscription = Subscription.query.get(current_user.subscription_id) if current_user.subscription_id else None
    current_app.logger.info(f"User {current_user.id} subscription: {subscription}")

    # Retrieve the user's one-time purchases
    one_time_purchases = OneTimePurchase.query.filter_by(user_id=current_user.id).all()
    current_app.logger.info(f"User {current_user.id} one-time purchases: {one_time_purchases}")

    # Determine if the user has access
    has_access = subscription is not None or any(purchase.signals_remaining > 0 for purchase in one_time_purchases)
    current_app.logger.info(f"User {current_user.id} has access: {has_access}")

    if not has_access:
        flash('You need a subscription or a one-time purchase to access this service.', 'warning')
        return redirect(url_for('main.subscribe'))

    form = QuickSignalForm()
    signal = None

    if form.validate_on_submit():
        selected_pack_id = request.form.get('selected_pack_id')
        if selected_pack_id:
            selected_pack = OneTimePurchase.query.get(selected_pack_id)
            if selected_pack and selected_pack.signals_remaining > 0:
                # Use the selected pack for generating signals
                signal = generate_signal(form.cryptocurrency.data, form.timeframe.data, pack=selected_pack)
                # Optionally, decrement the signals_remaining
                selected_pack.signals_remaining -= 1
                db.session.commit()
            else:
                flash('Selected pack is invalid or has no remaining signals.', 'danger')
                return redirect(url_for('main.quick_signal'))
        else:
            # Handle cases without a specific pack selection, possibly using subscription
            signal = generate_signal(form.cryptocurrency.data, form.timeframe.data)

    return render_template(
        'services/quick_signal.html',
        form=form,
        signal=signal,
        subscription=subscription,
        one_time_purchases=one_time_purchases
    )

@main_bp.route('/technology')
@login_required
def technology():
    return render_template('technology.html')

@main_bp.route('/refund-policy')
def refund_policy():
    return render_template('refund_policy.html')

@main_bp.route('/buy-signals', methods=['POST'])
@login_required
def buy_signals():
    data = request.get_json()
    selected_models = data.get('selected_models')  # Dictionary of plan_id: model_id

    if not selected_models:
        return jsonify({'error': 'Missing required data.'}), 400

    try:
        # Fetch all one-time purchase plans from the database
        one_time_plans = OneTimePlan.query.all()
        plan_map = {str(plan.id): plan for plan in one_time_plans}

        line_items = []
        for plan_id_str, model_id in selected_models.items():
            plan = plan_map.get(plan_id_str)
            if not plan:
                return jsonify({'error': f"Plan with ID {plan_id_str} does not exist."}), 400

            model = Model.query.get(model_id)
            if not model:
                return jsonify({'error': f"Model with ID {model_id} does not exist."}), 400

            # Calculate the additional cost based on the number of signals
            additional_cost = plan.signals * model.cost_per_signal
            final_price = plan.base_price + additional_cost

            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"One-Time Purchase: {plan.signals} Signals - {model.name} Model",
                    },
                    'unit_amount': int(final_price * 100),  # Convert to cents
                },
                'quantity': 1,
            })

        if not line_items:
            return jsonify({'error': 'No valid one-time purchase plans selected.'}), 400

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('main.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.subscribe', _external=True),
            metadata={
                'user_id': current_user.id,
                'selected_models': json.dumps(selected_models)  # Store as JSON string
            }
        )
        return jsonify({'url': checkout_session.url})
    except Exception as e:
        current_app.logger.error(f"Stripe Checkout Session creation failed: {e}")
        return jsonify({'error': 'An error occurred while creating the checkout session.'}), 500

@main_bp.route('/my_purchases')
@login_required
def my_purchases():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Number of purchases per page

        purchases_pagination = OneTimePurchase.query.filter_by(user_id=current_user.id)\
            .order_by(OneTimePurchase.purchase_date.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        purchases = purchases_pagination.items
    except Exception as e:
        current_app.logger.error(f"Error retrieving purchases for user {current_user.id}: {e}")
        flash('An error occurred while retrieving your purchases.', 'danger')
        return redirect(url_for('main.dashboard'))  # Redirect to a relevant page

    return render_template('my_purchases.html', purchases=purchases, pagination=purchases_pagination)

@main_bp.route('/api/one_time_purchases')
@login_required
def api_one_time_purchases():
    one_time_purchases = OneTimePurchase.query.filter_by(user_id=current_user.id).all()
    purchases_data = [
        {
            'id': purchase.id,
            'plan_name': purchase.plan.name,
            'signals_purchased': purchase.signals_purchased,
            'signals_remaining': purchase.signals_remaining
        }
        for purchase in one_time_purchases
    ]
    return jsonify(purchases_data)

@main_bp.route('/api/monthly_plan')
@login_required
def api_monthly_plan():
    subscription = current_user.subscription
    if subscription:
        subscription_data = {
            'plan_name': subscription.name
        }
    else:
        subscription_data = {
            'plan_name': None
        }
    return jsonify(subscription_data)