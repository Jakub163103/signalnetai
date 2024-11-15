from app.models import User

def create_system_user(app, db):
    with app.app_context():
        # Check if the "System" user already exists
        system_user = User.query.filter_by(username='System').first()
        if not system_user:
            # Create the "System" user
            system_user = User(
                username='System',
                email='system@signalnet.com',
                password='securepassword',  # Assign raw password; relies on User model's setter to hash
                country='US'  # Provide a default country code, e.g., 'US' for the United States
            )
            db.session.add(system_user)
            try:
                db.session.commit()
                print("System user created successfully.")
            except Exception as e:
                db.session.rollback()
                print(f"Failed to create System user: {e}")
        else:
            print("System user already exists.")

if __name__ == '__main__':
    from app import create_app, db
    app = create_app()
    create_system_user(app, db) 