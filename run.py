from app import create_app, db
from app.models import User
from create_system_user import create_system_user

app = create_app()

# Create the system user within the app context before running the server
with app.app_context():
    create_system_user(app, db)

if __name__ == '__main__':
    app.run(debug=True)
