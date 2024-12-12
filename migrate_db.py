from app import app, db
from flask_migrate import Migrate, upgrade

# Initialize Flask-Migrate
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        # Add the new column if it doesn't exist
        with db.engine.connect() as conn:
            conn.execute('ALTER TABLE budget_item ADD COLUMN IF NOT EXISTS description VARCHAR(200)')
        
        print("Database migration completed successfully!")
