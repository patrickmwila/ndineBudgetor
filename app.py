from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from functools import wraps
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os
from dotenv import load_dotenv
import csv
from io import StringIO, BytesIO

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key-for-development')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///budget.db')
app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Disable CSRF for GET requests
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)

# Email configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Add min function to Jinja2 environment
app.jinja_env.globals.update(min=min)

db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()
csrf.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
db.init_app(app)
mail.init_app(app)

# Create serializer for password reset tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Currency configuration
SUPPORTED_CURRENCIES = {
    'ZMW': 'Zambian Kwacha',
    'USD': 'US Dollar',
    'EUR': 'Euro',
    'GBP': 'British Pound',
    'ZAR': 'South African Rand'
}

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    default_currency = db.Column(db.String(3), default='ZMW')
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)
    savings = db.relationship('Saving', backref='user', lazy=True)
    investments = db.relationship('Investment', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def get_reset_token(self):
        """Generate a password reset token"""
        return serializer.dumps(self.email, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, max_age=3600):  # Token expires after 1 hour
        """Verify the password reset token"""
        try:
            email = serializer.loads(token, salt='password-reset-salt', max_age=max_age)
            return User.query.filter_by(email=email).first()
        except:
            return None

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'income' or 'expense'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budget_items = db.relationship('BudgetItem', backref='category', lazy=True)
    
    @staticmethod
    def get_default_categories():
        return [
            {'name': 'Salary', 'type': 'income'},
            {'name': 'Freelance', 'type': 'income'},
            {'name': 'Investment', 'type': 'income'},
            {'name': 'Other Income', 'type': 'income'},
            {'name': 'Rent', 'type': 'expense'},
            {'name': 'Utilities', 'type': 'expense'},
            {'name': 'Groceries', 'type': 'expense'},
            {'name': 'Transportation', 'type': 'expense'},
            {'name': 'Entertainment', 'type': 'expense'},
            {'name': 'Healthcare', 'type': 'expense'},
            {'name': 'Shopping', 'type': 'expense'},
            {'name': 'Other Expenses', 'type': 'expense'}
        ]

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type = db.Column(db.String(50), nullable=False)  # 'income' or 'expense'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)  # Made nullable
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='ZMW')
    source = db.Column(db.String(20), nullable=False)  # 'bank', 'mobile_money', or 'cash'
    archived = db.Column(db.Boolean, default=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='ZMW')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('BudgetItem', backref='budget', lazy=True)
    archived = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BudgetItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    budget_id = db.Column(db.Integer, db.ForeignKey('budget.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    planned_amount = db.Column(db.Float, nullable=False)
    spent_amount = db.Column(db.Float, default=0.0)
    archived = db.Column(db.Boolean, default=False)

class Saving(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'bank', 'mobile_money', 'cash'
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='ZMW')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'stocks', 'bonds', 'tbills', etc.
    initial_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='ZMW')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def check_session_timeout():
    if 'last_activity' in session:
        last_activity = datetime.fromisoformat(session['last_activity'])
        if datetime.now() - last_activity > timedelta(minutes=10):
            session.clear()
            return True
    session['last_activity'] = datetime.now().isoformat()
    return False

def check_timeout(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            if check_session_timeout():
                logout_user()
                flash('Your session has expired. Please login again.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return f(*args, **kwargs)  # Allow the function to handle non-authenticated users
    return decorated_function

# Add context processor to provide current year to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Password validation
def validate_password(password):
    """
    Validate password strength
    Returns (bool, str) tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"
    
    # Check for common patterns
    common_patterns = ['password', '123456', 'qwerty', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        return False, "Password contains common patterns that are not allowed"
    
    return True, ""

# Authentication routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Password validation
        is_valid, error_message = validate_password(password)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create default categories for the new user
        default_categories = Category.get_default_categories()
        for cat_data in default_categories:
            category = Category(
                name=cat_data['name'],
                type=cat_data['type'],
                user_id=user.id
            )
            db.session.add(category)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            session.permanent = True  # Enable session expiry
            session['last_activity'] = datetime.now().isoformat()
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password', 'error')
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# Main routes
@app.route('/')
@login_required
@check_timeout
def index():
    # Get current month's budget
    current_month = date.today().replace(day=1)
    current_budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        archived=False
    ).first()
    
    # Initialize budget variables
    total_spent = 0
    budget_remaining = 0
    
    if current_budget:
        # Calculate total spent for current budget
        budget_items = BudgetItem.query.filter_by(budget_id=current_budget.id, archived=False).all()
        total_spent = sum(item.spent_amount for item in budget_items)
        current_budget.total_spent = total_spent
        budget_remaining = current_budget.total_amount - total_spent

    # Get latest savings balances with their currencies
    latest_savings = {
        'bank': Saving.query.filter_by(user_id=current_user.id, type='bank')
                          .order_by(Saving.date.desc()).first(),
        'mobile_money': Saving.query.filter_by(user_id=current_user.id, type='mobile_money')
                                 .order_by(Saving.date.desc()).first(),
        'cash': Saving.query.filter_by(user_id=current_user.id, type='cash')
                         .order_by(Saving.date.desc()).first()
    }
    
    # Calculate balances with their respective currencies
    bank_balance = latest_savings['bank'].amount if latest_savings['bank'] else 0
    bank_currency = latest_savings['bank'].currency if latest_savings['bank'] else current_user.default_currency
    
    mobile_money_balance = latest_savings['mobile_money'].amount if latest_savings['mobile_money'] else 0
    mobile_money_currency = latest_savings['mobile_money'].currency if latest_savings['mobile_money'] else current_user.default_currency
    
    cash_balance = latest_savings['cash'].amount if latest_savings['cash'] else 0
    cash_currency = latest_savings['cash'].currency if latest_savings['cash'] else current_user.default_currency
    
    # Get the most recent savings entry for currency
    most_recent_saving = Saving.query.filter_by(user_id=current_user.id)\
        .order_by(Saving.date.desc())\
        .first()
    
    total_income = bank_balance + mobile_money_balance + cash_balance
    income_currency = most_recent_saving.currency if most_recent_saving else current_user.default_currency
    
    # Get investment totals with currency
    investments = Investment.query.filter_by(user_id=current_user.id).all()
    total_market_value = sum(inv.current_value for inv in investments)
    total_initial_investment = sum(inv.initial_value for inv in investments)
    investment_currency = investments[0].currency if investments else current_user.default_currency
    
    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc())\
        .limit(5)\
        .all()
    
    return render_template('index.html',
                         current_budget=current_budget,
                         bank_balance=bank_balance,
                         bank_currency=bank_currency,
                         mobile_money_balance=mobile_money_balance,
                         mobile_money_currency=mobile_money_currency,
                         cash_balance=cash_balance,
                         cash_currency=cash_currency,
                         total_income=total_income,
                         income_currency=income_currency,
                         total_market_value=total_market_value,
                         total_initial_investment=total_initial_investment,
                         investment_currency=investment_currency,
                         recent_transactions=recent_transactions,
                         budget_remaining=budget_remaining)

@app.route('/dashboard')
@login_required
@check_timeout
def dashboard():
    # Get current month's budget and remaining balance
    current_month = date.today().replace(day=1)
    budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        archived=False
    ).first()
    
    budget_remaining = 0
    total_budget = 0
    if budget:
        budget_items = BudgetItem.query.filter_by(
            budget_id=budget.id,
            archived=False
        ).all()
        
        total_spent = sum(item.spent_amount for item in budget_items)
        total_budget = budget.total_amount
        budget_remaining = total_budget - total_spent

    # Get recent transactions
    recent_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()

    # Get financial sources total
    financial_sources = FinancialSource.query.filter_by(user_id=current_user.id).all()
    total_balance = sum(source.balance for source in financial_sources)

    return render_template('dashboard.html',
                         recent_transactions=recent_transactions,
                         total_balance=total_balance,
                         budget_remaining=budget_remaining,
                         total_budget=total_budget,
                         budget=budget)

@app.route('/transactions', methods=['GET'])
@login_required
@check_timeout
def transactions():
    # GET request - show transactions list
    selected_currency = request.args.get('currency', current_user.default_currency)
    transactions = Transaction.query.filter_by(
        user_id=current_user.id,
        currency=selected_currency,
        archived=False
    ).order_by(Transaction.date.desc()).all()
    
    # Get categories for the form
    expense_categories = Category.query.filter_by(user_id=current_user.id, type='expense').order_by(Category.name).all()
    income_categories = Category.query.filter_by(user_id=current_user.id, type='income').order_by(Category.name).all()
    
    return render_template('transactions.html', 
                         transactions=transactions,
                         expense_categories=expense_categories,
                         income_categories=income_categories,
                         selected_currency=selected_currency,
                         currencies=SUPPORTED_CURRENCIES,
                         today=date.today())

@app.route('/api/categories/<type>')
@login_required
@check_timeout
def get_categories(type):
    categories = Category.query.filter_by(
        user_id=current_user.id,
        type=type
    ).order_by(Category.name).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in categories])

@app.route('/transaction/delete/<int:id>', methods=['POST'])
@login_required
@check_timeout
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized access'})
    
    try:
        # Revert budget changes if expense
        if transaction.type == 'expense':
            current_month = transaction.date.replace(day=1)
            budget = Budget.query.filter_by(
                user_id=current_user.id,
                month=current_month,
                archived=False
            ).first()
            
            if budget:
                budget_item = BudgetItem.query.filter_by(
                    budget_id=budget.id,
                    category_id=transaction.category_id,
                    archived=False
                ).first()
                
                if budget_item:
                    budget_item.spent_amount -= transaction.amount
        
        # Revert finance changes
        saving = Saving.query.filter_by(
            user_id=current_user.id,
            type=transaction.source
        ).order_by(Saving.date.desc()).first()
        
        if saving:
            new_saving = Saving(
                type=transaction.source,
                amount=saving.amount - transaction.amount if transaction.type == 'income' else saving.amount + transaction.amount,
                currency=transaction.currency,
                description=f"Reverted transaction: {transaction.description}",
                user_id=current_user.id
            )
            db.session.add(new_saving)
        
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Transaction deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting transaction: {str(e)}'})

# Budget routes
@app.route('/budget')
@login_required
@check_timeout
def budget():
    # Get current month's budget
    current_month = date.today().replace(day=1)
    
    # Debug print for categories
    print("Checking categories...")
    expense_categories = Category.query.filter_by(
        user_id=current_user.id,
        type='expense'
    ).order_by(Category.name).all()
    print(f"Found {len(expense_categories)} categories")
    for cat in expense_categories:
        print(f"Category: {cat.name} (ID: {cat.id})")
    
    budget = Budget.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        archived=False
    ).first()

    if budget:
        # Get budget items
        budget_items = BudgetItem.query.filter_by(
            budget_id=budget.id,
            archived=False
        ).all()

        # Calculate total spent and remaining amounts
        total_spent = sum(item.spent_amount for item in budget_items)
        total_planned = sum(item.planned_amount for item in budget_items)
        total_remaining = budget.total_amount - total_planned
        available_for_budget = budget.total_amount - total_planned
    else:
        budget_items = []
        total_spent = 0
        total_planned = 0
        total_remaining = 0
        available_for_budget = 0

    return render_template('budget/index.html',
                         budget=budget,
                         budget_items=budget_items,
                         categories=expense_categories,  # Changed to use our debug variable
                         current_month=current_month,
                         currencies=SUPPORTED_CURRENCIES,
                         total_spent=total_spent,
                         total_planned=total_planned,
                         total_remaining=total_remaining,
                         available_for_budget=available_for_budget)

@app.route('/budget/create', methods=['POST'])
@login_required
@check_timeout
def create_budget():
    if not request.form:
        flash('No form data received', 'error')
        return redirect(url_for('budget'))
        
    try:
        # Get and validate form data
        total_amount = request.form.get('total_amount')
        currency = request.form.get('currency')
        
        if not total_amount or not currency:
            flash('Please provide both total amount and currency', 'error')
            return redirect(url_for('budget'))
            
        total_amount = float(total_amount)
        if total_amount <= 0:
            flash('Budget amount must be greater than 0', 'error')
            return redirect(url_for('budget'))
        
        # Check if a budget already exists for this month
        current_month = date.today().replace(day=1)
        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            month=current_month,
            archived=False
        ).first()
        
        if existing_budget:
            flash('A budget already exists for this month', 'error')
            return redirect(url_for('budget'))
        
        # Create new budget
        new_budget = Budget(
            month=current_month,
            total_amount=total_amount,
            currency=currency,
            user_id=current_user.id
        )
        db.session.add(new_budget)
        db.session.commit()
        
        flash('Budget created successfully!', 'success')
        return redirect(url_for('budget'))
        
    except ValueError:
        flash('Invalid amount format', 'error')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error creating budget: {str(e)}')
        flash('An error occurred while creating the budget', 'error')
    
    return redirect(url_for('budget'))

@app.route('/budget/item/edit', methods=['POST'])
@login_required
@check_timeout
def edit_budget_item():
    item_id = request.form['item_id']
    item = BudgetItem.query.get_or_404(item_id)
    
    # Check if user owns this budget item
    if item.budget.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    new_amount = float(request.form['planned_amount'])
    
    # Calculate current total of all budget items excluding this item
    current_items_total = db.session.query(db.func.sum(BudgetItem.planned_amount))\
        .filter_by(budget_id=item.budget_id, archived=False)\
        .filter(BudgetItem.id != item_id).scalar() or 0
    
    # Check if editing this item would exceed the budget
    if current_items_total + new_amount > item.budget.total_amount:
        return jsonify({
            'status': 'error',
            'message': f'This budget item ({item.budget.currency} {new_amount:.2f}) would exceed your total budget. '
                      f'You can allocate up to {item.budget.currency} {(item.budget.total_amount - current_items_total):.2f}.'
        }), 400
    
    # Update the item
    item.planned_amount = new_amount
    item.category_id = request.form['category_id']
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Budget item updated successfully'})

@app.route('/budget/item/add', methods=['POST'])
@login_required
@check_timeout
def add_budget_item():
    try:
        budget_id = request.form.get('budget_id')
        category_id = request.form.get('category_id')
        planned_amount = float(request.form.get('planned_amount'))
        
        if not all([budget_id, category_id, planned_amount]):
            flash('Please fill in all required fields', 'error')
            return redirect(url_for('budget'))
            
        # Verify budget exists and belongs to user
        budget = Budget.query.filter_by(
            id=budget_id,
            user_id=current_user.id,
            archived=False
        ).first()
        
        if not budget:
            flash('Budget not found', 'error')
            return redirect(url_for('budget'))
            
        # Calculate available amount
        existing_items = BudgetItem.query.filter_by(
            budget_id=budget_id,
            archived=False
        ).all()
        total_planned = sum(item.planned_amount for item in existing_items)
        available_amount = budget.total_amount - total_planned
        
        if planned_amount > available_amount:
            flash(f'Amount exceeds available budget. Maximum available: {budget.currency} {available_amount:.2f}', 'error')
            return redirect(url_for('budget'))
            
        # Check if item already exists
        existing_item = BudgetItem.query.filter_by(
            budget_id=budget_id,
            category_id=category_id,
            archived=False
        ).first()
        
        if existing_item:
            flash('A budget item for this category already exists', 'error')
            return redirect(url_for('budget'))
            
        # Create new budget item
        budget_item = BudgetItem(
            budget_id=budget_id,
            category_id=category_id,
            planned_amount=planned_amount,
            spent_amount=0
        )
        
        db.session.add(budget_item)
        db.session.commit()
        
        flash('Budget item added successfully!', 'success')
        
    except ValueError:
        flash('Invalid amount format', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding budget item: {str(e)}', 'error')
        
    return redirect(url_for('budget'))

@app.route('/budget/increase', methods=['POST'])
@login_required
@check_timeout
def increase_budget():
    budget_id = request.form.get('budget_id')
    amount = float(request.form.get('amount', 0))
    
    if not budget_id or amount <= 0:
        flash('Invalid budget increase request', 'error')
        return redirect(url_for('budget'))
    
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first()
    if not budget:
        flash('Budget not found', 'error')
        return redirect(url_for('budget'))
    
    budget.total_amount += amount
    db.session.commit()
    
    flash(f'Budget increased by {budget.currency} {amount:.2f}', 'success')
    return redirect(url_for('budget'))

@app.route('/budget/reset', methods=['POST'])
@login_required
@check_timeout
def reset_budget():
    budget_id = request.form['budget_id']
    new_amount = float(request.form['new_amount'])
    budget = Budget.query.get_or_404(budget_id)
    
    if budget.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    # Get total planned amount
    total_planned = db.session.query(db.func.sum(BudgetItem.planned_amount))\
        .filter_by(budget_id=budget_id, archived=False).scalar() or 0
    
    # Check if new amount would be less than current planned amounts
    if new_amount < total_planned:
        return jsonify({
            'status': 'error',
            'message': f'Cannot reset budget to {budget.currency} {new_amount:.2f} as it is less than your total planned '
                      f'amounts ({budget.currency} {total_planned:.2f}). Please adjust your budget items first.'
        }), 400
    
    # Update the budget
    budget.total_amount = new_amount
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Budget has been reset successfully'})

@app.route('/budget/archive/<int:budget_id>')
@login_required
@check_timeout
def archive_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('budget'))
    
    # Check if budget has any items before archiving
    if not budget.items:
        flash("Can't archive empty budget", 'error')
        return redirect(url_for('budget'))
    
    budget.archived = True
    db.session.commit()
    flash('Budget archived successfully!', 'success')
    return redirect(url_for('budget'))

@app.route('/budgets/archived')
@login_required
@check_timeout
def view_archived_budgets():
    # Get all archived budgets for the current user, ordered by month
    archived_budgets = Budget.query.filter_by(
        user_id=current_user.id,
        archived=True
    ).order_by(Budget.month.desc()).all()
    
    return render_template('archived_budgets.html', 
                         archived_budgets=archived_budgets)

@app.route('/budget/archive/<int:budget_id>', methods=['POST'])
@login_required
@check_timeout
def archive_budget_post(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
    
    # Check if budget has any items before archiving
    if not budget.items:
        return jsonify({'status': 'error', 'message': "Can't archive empty budget"}), 400
    
    budget.archived = True
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Budget archived successfully'})

@app.route('/budget/delete/<int:budget_id>', methods=['POST'])
@login_required
@check_timeout
def delete_budget(budget_id):
    try:
        budget = Budget.query.get_or_404(budget_id)
        
        # Security check: ensure user owns this budget
        if budget.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
        
        # Delete associated budget items first
        BudgetItem.query.filter_by(budget_id=budget.id).delete()
        
        # Delete the budget
        db.session.delete(budget)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Budget deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/budget/item/delete/<int:item_id>', methods=['POST'])
@login_required
@check_timeout
def delete_budget_item(item_id):
    try:
        budget_item = BudgetItem.query.get_or_404(item_id)
        
        # Security check: ensure user owns this budget item
        if budget_item.budget.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
        
        db.session.delete(budget_item)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Budget item deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/budget/item/update/<int:item_id>', methods=['POST'])
@login_required
@check_timeout
def update_budget_item(item_id):
    try:
        budget_item = BudgetItem.query.get_or_404(item_id)
        
        # Security check: ensure user owns this budget item
        if budget_item.budget.user_id != current_user.id:
            return jsonify({'status': 'error', 'message': 'Unauthorized access'}), 403
        
        data = request.get_json()
        
        # Validate input
        if not data or 'category_id' not in data or 'planned_amount' not in data:
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        try:
            planned_amount = float(data['planned_amount'])
            if planned_amount < 0:
                return jsonify({'status': 'error', 'message': 'Planned amount cannot be negative'}), 400
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid planned amount'}), 400
        
        # Update budget item
        budget_item.category_id = data['category_id']
        budget_item.planned_amount = planned_amount
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Budget item updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/budget/use-template/<int:budget_id>', methods=['POST'])
@login_required
@check_timeout
def use_budget_template(budget_id):
    try:
        # Get the template budget
        template_budget = Budget.query.get_or_404(budget_id)
        
        # Security check: ensure user owns this budget
        if template_budget.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized access'}), 403
            
        # Create new budget for current month
        current_month = date.today().replace(day=1)
        
        # Check if budget already exists for current month
        existing_budget = Budget.query.filter_by(
            user_id=current_user.id,
            month=current_month,
            archived=False
        ).first()
        
        if existing_budget:
            return jsonify({
                'success': False,
                'message': 'A budget already exists for this month'
            }), 400
            
        # Create new budget using template
        new_budget = Budget(
            month=current_month,
            total_amount=template_budget.total_amount,
            currency=template_budget.currency,
            user_id=current_user.id,
            archived=False
        )
        db.session.add(new_budget)
        db.session.flush()  # Get the new budget ID
        
        # Copy budget items
        for template_item in template_budget.items:
            new_item = BudgetItem(
                budget_id=new_budget.id,
                category_id=template_item.category_id,
                planned_amount=template_item.planned_amount,
                spent_amount=0.0  # Reset spent amount for new budget
            )
            db.session.add(new_item)
            
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Budget template applied successfully',
            'redirect': url_for('budget')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# Finance module routes
@app.route('/finance')
@login_required
@check_timeout
def finance():
    # Get savings by type
    savings = {
        'bank': Saving.query.filter_by(user_id=current_user.id, type='bank').order_by(Saving.date.desc()).first(),
        'mobile_money': Saving.query.filter_by(user_id=current_user.id, type='mobile_money').order_by(Saving.date.desc()).first(),
        'cash': Saving.query.filter_by(user_id=current_user.id, type='cash').order_by(Saving.date.desc()).first()
    }
    
    # Get investments
    investments = Investment.query.filter_by(user_id=current_user.id).all()
    
    return render_template('finance/index.html', 
                         savings=savings,
                         investments=investments,
                         currencies=SUPPORTED_CURRENCIES)

@app.route('/finance/savings/update', methods=['POST'])
@login_required
@check_timeout
def update_savings():
    saving_type = request.form['type']
    amount = float(request.form['amount'])
    currency = request.form['currency']
    description = request.form['description']
    
    saving = Saving(
        type=saving_type,
        amount=amount,
        currency=currency,
        description=description,
        user_id=current_user.id
    )
    db.session.add(saving)
    db.session.commit()
    
    flash('Savings updated successfully!', 'success')
    return redirect(url_for('finance'))

@app.route('/finance/investment/add', methods=['POST'])
@login_required
@check_timeout
def add_investment():
    investment = Investment(
        type=request.form['type'],
        initial_value=float(request.form['initial_value']),
        current_value=float(request.form['current_value']),
        currency=request.form['currency'],
        description=request.form['description'],
        user_id=current_user.id
    )
    db.session.add(investment)
    db.session.commit()
    
    flash('Investment added successfully!', 'success')
    return redirect(url_for('finance'))

@app.route('/finance/investment/update/<int:investment_id>', methods=['POST'])
@login_required
@check_timeout
def update_investment(investment_id):
    investment = Investment.query.get_or_404(investment_id)
    if investment.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('finance'))
    
    investment.current_value = float(request.form['current_value'])
    investment.last_updated = datetime.utcnow()
    db.session.commit()
    
    flash('Investment updated successfully!', 'success')
    return redirect(url_for('finance'))

@app.route('/transactions/create', methods=['POST'])
@login_required
@check_timeout
def create_transaction():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            description = request.form['description']
            transaction_type = request.form['type']
            category_id = request.form.get('category_id')
            source = request.form.get('source')
            
            if not all([amount, description, transaction_type, source]):
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('transactions'))

            # Create the transaction
            transaction = Transaction(
                amount=amount,
                description=description,
                type=transaction_type,
                category_id=category_id if category_id else None,
                source=source,
                user_id=current_user.id,
                currency=current_user.default_currency,
                date=datetime.now()
            )
            db.session.add(transaction)

            # If it's an expense, update the budget
            if transaction_type == 'expense' and category_id:
                # Get current month's budget
                current_month = date.today().replace(day=1)
                budget = Budget.query.filter_by(
                    user_id=current_user.id,
                    month=current_month,
                    archived=False
                ).first()

                if not budget:
                    # Create a new budget for this month if it doesn't exist
                    budget = Budget(
                        month=current_month,
                        total_amount=0,  # Start with 0, can be updated later
                        currency=current_user.default_currency,
                        user_id=current_user.id
                    )
                    db.session.add(budget)
                    db.session.flush()  # Get the budget ID
                    flash(f'Created new budget for {current_month.strftime("%B %Y")}', 'info')

                # Find or create budget item for this category
                budget_item = BudgetItem.query.filter_by(
                    budget_id=budget.id,
                    category_id=category_id,
                    archived=False
                ).first()

                if not budget_item:
                    # Create a new budget item if it doesn't exist
                    budget_item = BudgetItem(
                        budget_id=budget.id,
                        category_id=category_id,
                        planned_amount=amount,  # Set initial planned amount to this expense
                        spent_amount=0
                    )
                    db.session.add(budget_item)
                    db.session.flush()
                    flash(f'Created new budget item for {Category.query.get(category_id).name}', 'info')

                # Update spent amount
                budget_item.spent_amount = float(budget_item.spent_amount or 0) + amount
                db.session.add(budget_item)
                
                # Check if over budget and flash appropriate message
                if budget_item.spent_amount > budget_item.planned_amount:
                    remaining = budget_item.planned_amount - budget_item.spent_amount
                    flash(f'Warning: You have exceeded the budget for {budget_item.category.name} by {budget.currency} {abs(remaining):.2f}', 'warning')
                else:
                    remaining = budget_item.planned_amount - budget_item.spent_amount
                    flash(f'Budget remaining for {budget_item.category.name}: {budget.currency} {remaining:.2f}', 'info')

            # Update savings/finance based on transaction type
            if transaction_type == 'income':
                # For income, add to the specified source
                saving = Saving.query.filter_by(
                    user_id=current_user.id,
                    type=source
                ).first()
                
                if saving:
                    saving.amount = float(saving.amount or 0) + amount
                    db.session.add(saving)
                else:
                    # Create new saving record if doesn't exist
                    saving = Saving(
                        type=source,
                        amount=amount,
                        currency=current_user.default_currency,
                        user_id=current_user.id,
                        description=f'Updated from transaction: {description}'
                    )
                    db.session.add(saving)
            else:
                # For expense, subtract from the specified source
                saving = Saving.query.filter_by(
                    user_id=current_user.id,
                    type=source
                ).first()
                
                if saving:
                    saving.amount = float(saving.amount or 0) - amount
                    db.session.add(saving)
                    if saving.amount < 0:
                        flash(f'Warning: Your {source} balance is negative!', 'warning')
                else:
                    flash(f'Error: Could not find {source} account to deduct from', 'error')
                    return redirect(url_for('transactions'))

            db.session.commit()
            flash('Transaction created successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'Error creating transaction: {str(e)}')
            flash('Error creating transaction. Please try again.', 'error')
            
        return redirect(url_for('transactions'))

@app.route('/export_transactions')
@login_required
def export_transactions():
    """Export user's transactions to CSV"""
    # Create a StringIO object to write CSV data
    si = StringIO()
    cw = csv.writer(si)
    
    # Write headers
    cw.writerow(['Date', 'Type', 'Amount', 'Currency', 'Description', 'Category', 'Source'])
    
    # Get all transactions for the user
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
    
    # Write transaction data
    for transaction in transactions:
        category_name = transaction.category.name if transaction.category else 'N/A'
        cw.writerow([
            transaction.date.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.type,
            transaction.amount,
            transaction.currency,
            transaction.description,
            category_name,
            transaction.source
        ])
    
    # Create the response
    output = si.getvalue()
    si.close()
    
    # Generate filename with current timestamp
    filename = f'transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    # Convert string to bytes
    bytes_output = BytesIO()
    bytes_output.write(output.encode('utf-8-sig'))  # Use UTF-8 with BOM for Excel compatibility
    bytes_output.seek(0)
    
    return send_file(
        bytes_output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

def send_reset_email(user):
    """Send password reset email to user"""
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request, please ignore this email.
The link will expire in 1 hour.
'''
    mail.send(msg)

@app.route('/reset_password', methods=['GET', 'POST'])
def request_reset():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No account found with that email address.', 'error')
    
    return render_template('auth/reset_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('request_reset'))
    
    if request.method == 'POST':
        password = request.form['password']
        
        # Password validation
        is_valid, error_message = validate_password(password)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('reset_password', token=token))
        
        user.set_password(password)
        db.session.commit()
        flash('Your password has been updated! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/reset_password.html')

@app.route('/create_default_categories')
@login_required
def create_default_categories():
    # Check if user already has categories
    existing_categories = Category.query.filter_by(user_id=current_user.id).count()
    if existing_categories == 0:
        default_categories = Category.get_default_categories()
        for cat_data in default_categories:
            category = Category(
                name=cat_data['name'],
                type=cat_data['type'],
                user_id=current_user.id
            )
            db.session.add(category)
        db.session.commit()
        flash('Default categories have been created.', 'success')
    else:
        flash('You already have categories set up.', 'info')
    return redirect(url_for('budget'))

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username=os.getenv('ADMIN_USERNAME', 'admin')).first()
        if not admin_user:
            admin_user = User(
                username=os.getenv('ADMIN_USERNAME'),
                email=os.getenv('ADMIN_EMAIL'),
                default_currency=os.getenv('ADMIN_DEFAULT_CURRENCY')
            )
            admin_user.set_password(os.getenv('ADMIN_PASSWORD'))
            
            # Create default categories for admin user
            for category_data in Category.get_default_categories():
                category = Category(
                    name=category_data['name'],
                    type=category_data['type'],
                    user_id=1  # This will be the admin user's ID
                )
                db.session.add(category)
            
            db.session.add(admin_user)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
