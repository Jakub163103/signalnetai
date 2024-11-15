from flask import Flask
from config import DevelopmentConfig
from dotenv import load_dotenv
import logging
import os
import stripe
from .filters import nl2br  # Import the custom filter
from .extensions import db, migrate, login_manager, csrf, mail

load_dotenv()

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLITE_DATABASE_URI')

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    handler = logging.FileHandler('app.log')
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.errors import errors_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(errors_bp)

    # Create upload folder if it doesn't exist
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Import User model for user_loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_unread_notifications_count():
        from app.utils import get_unread_notifications_count
        return dict(unread_notifications_count=get_unread_notifications_count())

    # Register the custom filter
    app.jinja_env.filters['nl2br'] = nl2br

    # Set Stripe API key
    stripe.api_key = app.config['STRIPE_SECRET_KEY']

    return app
