import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import db
from app.models import Model
from app import create_app

def seed_models():
    app = create_app()
    with app.app_context():
        models = [
            {'name': 'Trend Analysis Model', 'cost_per_signal': 0},
            {'name': 'Pattern Recognition Model', 'cost_per_signal': 0.1},
            {'name': 'ML-based Predictive Model', 'cost_per_signal': 0.3},
            # Add more models as needed
        ]

        for model_data in models:
            existing_model = Model.query.filter_by(name=model_data['name']).first()
            if not existing_model:
                new_model = Model(
                    name=model_data['name'],
                    cost_per_signal=model_data['cost_per_signal']
                )
                db.session.add(new_model)
                print(f"Added model: {new_model.name}")
            else:
                print(f"Model {existing_model.name} already exists.")

        try:
            db.session.commit()
            print("Models seeded successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"Failed to seed models: {e}")

if __name__ == '__main__':
    seed_models()