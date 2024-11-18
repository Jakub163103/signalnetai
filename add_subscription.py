from app import db
from app.models import Subscription
from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Define the subscription plans with features and stripe_price_id
plans = [
    {
        "name": "Basic",
        "price": 9.99,
        "stripe_price_id": os.getenv("BASIC_PRICE_ID"),
        "features": [
            "Up to 5 signals per day",
            "Community forum access",
            "Basic trend analysis model"
        ]
    },
    {
        "name": "Pro",
        "price": 19.99,
        "stripe_price_id": os.getenv("PRO_PRICE_ID"),
        "features": [
            "Up to 20 signals per day",
            "Priority email support",
            "Intermediate pattern recognition model"
        ]
    },
    {
        "name": "Professional",
        "price": 49.99,
        "stripe_price_id": os.getenv("PROFESSIONAL_PRICE_ID"),
        "features": [
            "Up to 1000 signals per day",
            "24/7 dedicated support",
            "Machine learning-based predictive model"
        ]
    }
]

def add_subscriptions():
    app = create_app()
    with app.app_context():
        try:
            for plan in plans:
                # Check if the subscription already exists to prevent duplicates
                existing_plan = Subscription.query.filter_by(name=plan["name"]).first()
                if existing_plan:
                    print(f"Subscription '{plan['name']}' already exists. Skipping.")
                    continue

                subscription = Subscription(
                    name=plan["name"],
                    price=plan["price"],
                    stripe_price_id=plan["stripe_price_id"],
                    features=','.join(plan["features"]),
                    signals_per_day=1000 if plan["name"] == "Professional" else 20 if plan["name"] == "Pro" else 5  # Example logic
                )
                db.session.add(subscription)

            # Commit the changes to the database
            db.session.commit()
            print("Subscription plans added successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")

if __name__ == '__main__':
    add_subscriptions()
