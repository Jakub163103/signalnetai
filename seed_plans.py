# app/seed_plans.py

import os
from app import db
from app.models import OneTimePlan

def seed_one_time_plans():
    plans = [
        {'id': 1, 'name': 'Starter Pack', 'base_price': 15.00, 'signals': 10},
        {'id': 2, 'name': 'Growth Pack', 'base_price': 60.00, 'signals': 50},
        {'id': 3, 'name': 'Advanced Pack', 'base_price': 120.00, 'signals': 100},
        {'id': 4, 'name': 'Premium Pack', 'base_price': 220.00, 'signals': 200}
    ]

    for plan_data in plans:
        existing_plan = OneTimePlan.query.get(plan_data['id'])
        if not existing_plan:
            plan = OneTimePlan(
                id=plan_data['id'],
                name=plan_data['name'],
                base_price=plan_data['base_price'],
                signals=plan_data['signals']
            )
            db.session.add(plan)
            print(f"Added one-time plan: {plan.name}")
        else:
            print(f"One-time plan '{existing_plan.name}' already exists.")

    try:
        db.session.commit()
        print("One-time plans seeded successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Failed to seed one-time plans: {e}")

if __name__ == '__main__':
    # Ensure the app context is available
    os.environ.setdefault('FLASK_APP', 'app.py')  # Replace 'app.py' with your main app file if different
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'  # Update as needed
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        seed_one_time_plans()