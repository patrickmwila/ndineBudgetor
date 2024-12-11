# ndineBudgetor - Personal Finance Web Application Guide

## Table of Contents
1. [Application Architecture](#application-architecture)
2. [Database Schema](#database-schema)
3. [Project Structure](#project-structure)
4. [Dependencies](#dependencies)
5. [Development Setup](#development-setup)
6. [Database Management](#database-management)
7. [Authentication System](#authentication-system)
8. [Frontend Architecture](#frontend-architecture)
9. [Deployment Guide](#deployment-guide)
10. [Extending the Application](#extending-the-application)

## Application Architecture

### Overview
ndineBudgetor is a Flask-based personal finance management application with the following core components:

- **Backend**: Python Flask application
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Bootstrap 5 with JavaScript
- **Authentication**: Flask-Login
- **Session Management**: Flask Session with timeout
- **UI Components**: SweetAlert2 for notifications

### Core Features
1. User Authentication & Authorization
2. Budget Management
3. Transaction Tracking
4. Financial Analytics
5. Investment Tracking
6. Multi-currency Support

### Application Flow
1. User requests → Flask Routes
2. Route handlers → Database Operations
3. Database results → Template Rendering
4. Template → User Interface

## Database Schema

### Models Overview

#### User Model
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    default_currency = db.Column(db.String(3), default='ZMW')
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user')
    budgets = db.relationship('Budget', backref='user')
    savings = db.relationship('Saving', backref='user')
    investments = db.relationship('Investment', backref='user')
    categories = db.relationship('Category', backref='user')
```

#### Budget Model
```python
class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='ZMW')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    archived = db.Column(db.Boolean, default=False)
    
    # Relationships
    items = db.relationship('BudgetItem', backref='budget')
```

### Database Relationships
- One-to-Many relationships:
  - User → Transactions
  - User → Budgets
  - User → Categories
  - Budget → BudgetItems
  - Category → Transactions

### Adding New Models
1. Define model class in `app.py`
2. Add relationships
3. Create migration
4. Update database

Example:
```python
class NewFeature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Add to User model:
    # User.new_features = db.relationship('NewFeature', backref='user')
```

## Project Structure

```
ndineBudgetor/
├── app.py              # Main application file
├── budget.db           # SQLite database
├── requirements.txt    # Python dependencies
├── static/
│   ├── css/           # Custom CSS
│   └── js/            # Custom JavaScript
└── templates/
    ├── auth/          # Authentication templates
    ├── budget/        # Budget management templates
    ├── finance/       # Financial templates
    └── base.html      # Base template
```

## Dependencies

### Python Dependencies
```
Flask==2.0.1
Flask-SQLAlchemy==2.5.1
Flask-Login==0.5.0
Werkzeug==2.0.1
SQLAlchemy==1.4.23
```

### Frontend Dependencies
```html
<!-- Bootstrap 5 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>

<!-- SweetAlert2 -->
<link href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

<!-- Font Awesome -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/css/all.min.css">
```

## Development Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize database:
```bash
python
>>> from app import db
>>> db.create_all()
```

4. Run development server:
```bash
python app.py
```

## Database Management

### Creating New Tables
```python
# In app.py
class NewTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Add fields
    
# In Python shell
from app import db
db.create_all()
```

### Modifying Tables
1. Delete the table in Python shell:
```python
db.session.execute('DROP TABLE table_name')
db.session.commit()
```
2. Update model definition
3. Create new table:
```python
db.create_all()
```

### Relationships
- One-to-Many: Use `db.relationship()` with `backref`
- Many-to-Many: Use association table
- Cascade deletes: Add `cascade="all,delete"`

## Authentication System

### User Authentication Flow
1. Registration → Create user → Set password hash
2. Login → Verify credentials → Create session
3. Protected routes → Check login_required
4. Session timeout → Auto logout

### Adding Protected Routes
```python
@app.route('/protected')
@login_required
@check_timeout
def protected_route():
    # Your code here
```

## Frontend Architecture

### Template Inheritance
- Base template: `base.html`
- Child templates extend base
- Block structure:
  - title
  - content
  - scripts

### Styling Guide
1. Use Bootstrap classes first
2. Custom CSS in `static/css/style.css`
3. Page-specific styles in template blocks

### JavaScript Organization
1. Global functions in `static/js/main.js`
2. Page-specific scripts in template blocks
3. Use event delegation for dynamic elements

## Deployment Guide

### Ubuntu 18.04

1. Install dependencies:
```bash
sudo apt update
sudo apt install python3.6 python3-pip python3-venv nginx
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install Gunicorn:
```bash
pip install gunicorn
```

4. Configure Nginx:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

5. Create systemd service:
```ini
[Unit]
Description=ndineBudgetor
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/app
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

### Ubuntu Latest (22.04+)

1. Install dependencies:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx
```

2. Install and configure uWSGI:
```bash
pip install uwsgi
```

3. uWSGI configuration (uwsgi.ini):
```ini
[uwsgi]
module = app:app
master = true
processes = 4
socket = /tmp/ndineBudgetor.sock
chmod-socket = 660
vacuum = true
die-on-term = true
```

4. Nginx configuration:
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/tmp/ndineBudgetor.sock;
    }
}
```

### SSL Configuration (Both Versions)
1. Install Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
```

2. Obtain certificate:
```bash
sudo certbot --nginx -d your_domain.com
```

## Extending the Application

### Adding New Features

1. Plan the feature:
   - Database changes needed
   - New routes required
   - UI components needed

2. Database updates:
   - Add new models
   - Create relationships
   - Update existing models if needed

3. Create routes:
```python
@app.route('/new-feature')
@login_required
@check_timeout
def new_feature():
    # Implementation
```

4. Add templates:
   - Create new template file
   - Extend base.html
   - Add necessary blocks

5. Add static files:
   - CSS in static/css/
   - JavaScript in static/js/

### Best Practices

1. Database:
   - Always use relationships
   - Include foreign keys
   - Add indexes for frequently queried fields

2. Security:
   - Always check user ownership
   - Validate all inputs
   - Use CSRF protection
   - Implement rate limiting

3. UI/UX:
   - Follow Bootstrap patterns
   - Keep consistent styling
   - Use SweetAlert2 for notifications
   - Implement proper error handling

4. Code Organization:
   - Comment complex logic
   - Use meaningful variable names
   - Follow PEP 8 guidelines
   - Keep functions focused and small

### Testing New Features

1. Unit Tests:
```python
def test_new_feature():
    # Test implementation
```

2. Integration Tests:
```python
def test_feature_workflow():
    # Test complete workflow
```

3. Manual Testing Checklist:
   - Feature functionality
   - Security checks
   - UI responsiveness
   - Error handling
   - Performance impact

## Support and Maintenance

### Common Issues

1. Database Migrations:
```bash
# Backup database
sqlite3 budget.db .dump > backup.sql

# Restore if needed
cat backup.sql | sqlite3 budget.db
```

2. Session Issues:
- Clear sessions
- Reset user password
- Check timeout settings

3. Performance:
- Index heavily queried fields
- Optimize database queries
- Cache frequent operations

### Monitoring

1. Application Logs:
```python
app.logger.info('Action performed')
app.logger.error('Error occurred')
```

2. Error Tracking:
- Set up error emails
- Monitor application logs
- Track user reports

3. Performance Metrics:
- Response times
- Database query times
- Resource usage

## Contact Information

For support or questions, contact:
- Name: Patrick Mwila
- Role: ICT Innovations & Administrator, ICTAZ
- Email: patrickmwila.org@gmail.com
- Phone: +260 972 338 617
