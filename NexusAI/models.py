from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, default='Nexus Tech Solutions')
    address = db.Column(db.String(255), default='102 Tech Park, Outer Ring Road, Bengaluru, Karnataka')
    phone = db.Column(db.String(30), default='+91 80 4123 4567')
    email = db.Column(db.String(120), default='contact@nexustech.in')
    currency = db.Column(db.String(10), default='INR')
    tax_rate = db.Column(db.Float, default=18.0) # GST 18%
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', backref='company', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='Admin')
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    company_name = db.Column(db.String(120))
    city = db.Column(db.String(60), default='Mumbai')
    state = db.Column(db.String(60), default='Maharashtra')
    total_spent = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Active') # Active, Inactive, Lead
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('Sale', backref='customer', lazy=True)
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    department = db.Column(db.String(60), nullable=False) # Sales, Engineering, Operations, HR, Marketing
    position = db.Column(db.String(80), nullable=False)
    salary = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Active')
    hire_date = db.Column(db.Date, nullable=False)

    tasks = db.relationship('Task', backref='assigned_employee', lazy=True)
    leave_requests = db.relationship('LeaveRequest', backref='employee', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(60), nullable=False) # Hardware, Software, Services, Consulting
    price = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_level = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship('Sale', backref='product', lazy=True)
    inventory_logs = db.relationship('Inventory', backref='product', lazy=True)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    change_quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(120), nullable=False) # Sale, Restock, Return, Adjustment
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Completed') # Completed, Refunded, Pending
    region = db.Column(db.String(50), default='North India') # North India, West India, South India, East India

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    invoice_number = db.Column(db.String(50), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='Pending') # Paid, Pending, Overdue, Cancelled
    notes = db.Column(db.Text)
    pdf_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('InvoiceItem', backref='invoice', cascade='all, delete-orphan', lazy=True)

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    category = db.Column(db.String(60), nullable=False) # Marketing, Salaries, Operations, Software, Rent, Utilities
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50), default='Bank Transfer') # Bank Transfer, UPI, Credit Card, Cash
    vendor = db.Column(db.String(120))
    status = db.Column(db.String(20), default='Approved') # Approved, Pending, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    title = db.Column(db.String(150), nullable=False)
    meeting_date = db.Column(db.DateTime, default=datetime.utcnow)
    transcript = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    key_decisions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    assigned_to_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High, Urgent
    status = db.Column(db.String(20), default='To Do') # To Do, In Progress, Completed
    due_date = db.Column(db.Date)
    source = db.Column(db.String(50), default='Manual') # Manual, AI Meeting, AI Advisor, Low Stock
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) # Casual, Sick, Paid, Earned
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(30), default='info') # info, warning, success, danger, ai
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdvisorChat(db.Model):
    __tablename__ = 'advisor_chats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, default=1)
    title = db.Column(db.String(150), nullable=False, default='New Conversation')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('AdvisorMessage', backref='chat', cascade='all, delete-orphan', lazy=True, order_by='AdvisorMessage.created_at')

class AdvisorMessage(db.Model):
    __tablename__ = 'advisor_messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('advisor_chats.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False) # 'user' or 'ai'
    content = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.Text, nullable=True) # Optional JSON payload for structured cards/buttons
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

