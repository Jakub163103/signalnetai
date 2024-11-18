from app import db
from app.models import User
from werkzeug.security import generate_password_hash

def create_system_user(app, db):
    with app.app_context():
        system_email = 'system@signalnet.com'
        system_user = User.query.filter_by(email=system_email).first()
        if not system_user:
            system_user = User(
                email=system_email,
                password='',  # Consider setting a secure password or handling authentication appropriately
                country='US',  # Set a default country or choose appropriately
                role='System',
                is_admin=False
            )
            db.session.add(system_user)
            try:
                db.session.commit()
                app.logger.info('System user created successfully.')
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Error creating system user: {e}')
        else:
            app.logger.info('System user already exists.') 