import os
from app import app, db, Category, User
from werkzeug.security import generate_password_hash

# Delete existing database
db_file = 'budget.db'
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"Deleted existing {db_file}")

# Create new database with updated schema
with app.app_context():
    db.create_all()
    print("Created new database with updated schema")
    
    # Create default admin user
    admin_user = User(
        username='admin',
        email='admin@example.com',
        default_currency='ZMW',
        password_hash=generate_password_hash('admin')
    )
    db.session.add(admin_user)
    db.session.flush()  # This will assign an ID to admin_user
    
    # Create default categories for admin user
    default_categories = Category.get_default_categories()
    for cat_data in default_categories:
        category = Category(
            name=cat_data['name'], 
            type=cat_data['type'],
            user_id=admin_user.id
        )
        db.session.add(category)
    
    db.session.commit()
    print("Added default admin user and categories")
    
    print("\nYou can now log in with:")
    print("Username: admin")
    print("Password: admin")
    print("\nOr register a new user at: http://127.0.0.1:5000/register")
