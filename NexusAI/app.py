import os
import json
import base64
import werkzeug
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

from database import db, init_db
from models import (
    Company, User, Customer, Employee, Product, Inventory,
    Sale, Invoice, InvoiceItem, Expense, Meeting, Task, LeaveRequest, Notification,
    AdvisorChat, AdvisorMessage
)
from utils import format_currency, generate_invoice_pdf, generate_sales_report_pdf
from ml import predict_sales, forecast_inventory, analyze_expenses
from ai import (
    process_ai_query, get_today_ai_priorities, get_business_metrics,
    create_invoice, generate_email, summarize_meeting, create_task, get_sales_summary,
    generate_chat_title
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'nexusai_secret_key_2026')
db_path = os.path.abspath('data/nexusai.db').replace('\\', '/')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

# Jinja filter for currency formatting
@app.template_filter('inr')
def inr_filter(amount):
    return format_currency(amount)

def is_logged_in():
    return 'user_id' in session

def get_cid():
    return session.get('company_id', 1)

@app.context_processor
def inject_global_data():
    if is_logged_in():
        cid = get_cid()
        unread_notifications = Notification.query.filter_by(company_id=cid, is_read=False).count()
        user = User.query.get(session.get('user_id'))
        company = Company.query.get(cid) or Company.query.first()
        return {
            'logged_in': True,
            'current_user': user,
            'company': company,
            'unread_notifications_count': unread_notifications
        }
    return {'logged_in': False, 'unread_notifications_count': 0}

# ==========================================
# 1. PAGE ROUTES
# ==========================================

@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['company_id'] = user.company_id or 1
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        if request.is_json:
            return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        company_name = data.get('company_name', '').strip() or "My SME Company"

        if not username or not email or not password:
            if request.is_json:
                return jsonify({'error': 'Username, email and password are required'}), 400
            return render_template('register.html', error="Username, email and password are required.")

        if User.query.filter((User.email == email) | (User.username == username)).first():
            if request.is_json:
                return jsonify({'error': 'User with this email or username already exists'}), 400
            return render_template('register.html', error="User with this email or username already exists.")

        company = Company(name=company_name)
        db.session.add(company)
        db.session.commit()

        user = User(
            username=username,
            email=email,
            role="Admin",
            company_id=company.id
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['company_id'] = company.id

        if request.is_json:
            return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    cid = get_cid()
    metrics = get_business_metrics(cid)
    priorities = get_today_ai_priorities(cid)
    sales_ml = predict_sales(cid)
    exp_ml = analyze_expenses(cid)
    inv_forecast = forecast_inventory(cid)

    recent_sales = Sale.query.filter_by(company_id=cid).order_by(Sale.sale_date.desc()).limit(5).all()
    recent_tasks = Task.query.filter_by(company_id=cid).order_by(Task.due_date.asc()).limit(5).all()

    return render_template(
        'dashboard.html',
        metrics=metrics,
        priorities=priorities,
        sales_ml=sales_ml,
        exp_ml=exp_ml,
        inv_forecast=inv_forecast[:5],
        recent_sales=recent_sales,
        recent_tasks=recent_tasks
    )

@app.route('/ai')
def ai_advisor():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('ai.html')

@app.route('/meetings')
def meetings():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    meeting_list = Meeting.query.filter_by(company_id=cid).order_by(Meeting.meeting_date.desc()).limit(10).all()
    return render_template('meetings.html', meetings=meeting_list)

@app.route('/invoices')
def invoices():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    invoice_list = Invoice.query.filter_by(company_id=cid).order_by(Invoice.issue_date.desc()).limit(10).all()
    customers = Customer.query.filter_by(company_id=cid).order_by(Customer.name.asc()).limit(10).all()
    products = Product.query.filter_by(company_id=cid).order_by(Product.name.asc()).all()
    return render_template('invoices.html', invoices=invoice_list, customers=customers, products=products)

@app.route('/emails')
def emails():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    customers = Customer.query.filter_by(company_id=cid).order_by(Customer.name.asc()).limit(10).all()
    return render_template('emails.html', customers=customers)

@app.route('/customers')
def customers():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    customer_list = Customer.query.filter_by(company_id=cid).order_by(Customer.created_at.desc()).limit(10).all()
    return render_template('customers.html', customers=customer_list)

@app.route('/customers/add', methods=['POST'])
def add_customer():
    if not is_logged_in():
        if request.is_json:
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('login'))

    cid = get_cid()
    data = request.get_json(silent=True) or request.form

    name = data.get('name', '').strip()
    if not name:
        name = "New Client"

    company_name = data.get('company_name', '').strip() or "Client Org"
    email = data.get('email', '').strip() or f"contact@{name.lower().replace(' ', '')}.com"
    phone = data.get('phone', '').strip() or "+91 98765 43210"
    city = data.get('city', '').strip() or "Bengaluru"
    state = data.get('state', '').strip() or "Karnataka"

    cust = Customer(
        company_id=cid,
        name=name,
        company_name=company_name,
        email=email,
        phone=phone,
        city=city,
        state=state,
        status="Active"
    )
    db.session.add(cust)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'customer_id': cust.id, 'name': cust.name})
    return redirect(url_for('customers'))

@app.route('/sales')
def sales():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    sales_list = Sale.query.filter_by(company_id=cid).order_by(Sale.sale_date.desc()).limit(15).all()
    sales_ml = predict_sales(cid)
    sales_summary = get_sales_summary(cid)
    customers = Customer.query.filter_by(company_id=cid).order_by(Customer.name.asc()).all()
    products = Product.query.filter_by(company_id=cid).order_by(Product.name.asc()).all()

    # Calculate Month-by-Month Sales Breakdown
    all_sales = Sale.query.filter_by(company_id=cid).all()
    monthly_map = {}
    for s in all_sales:
        if s.sale_date:
            m_key = s.sale_date.strftime('%B %Y')
            m_sort = s.sale_date.strftime('%Y-%m')
            if m_key not in monthly_map:
                monthly_map[m_key] = {'month': m_key, 'total': 0.0, 'count': 0, 'sort_key': m_sort}
            monthly_map[m_key]['total'] += s.total_amount
            monthly_map[m_key]['count'] += 1

    monthly_breakdown = sorted(monthly_map.values(), key=lambda x: x['sort_key'], reverse=True)

    return render_template(
        'sales.html',
        sales=sales_list,
        sales_ml=sales_ml,
        summary=sales_summary,
        customers=customers,
        products=products,
        monthly_breakdown=monthly_breakdown
    )

@app.route('/sales/add', methods=['POST'])
def add_sale():
    if not is_logged_in():
        if request.is_json:
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('login'))

    cid = get_cid()
    data = request.get_json(silent=True) or request.form

    customer_id = data.get('customer_id')
    product_id = data.get('product_id')
    cust_name_input = data.get('customer_name', '').strip()
    prod_name_input = data.get('product_name', '').strip()

    try:
        amount = float(data.get('amount', 40000.0))
    except (ValueError, TypeError):
        amount = 40000.0

    try:
        quantity = int(data.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    region = data.get('region', 'North India')
    sale_date_str = data.get('sale_date')

    if sale_date_str:
        try:
            sale_date = datetime.strptime(sale_date_str, '%Y-%m-%d').date()
        except ValueError:
            sale_date = date.today()
    else:
        sale_date = date.today()

    # Dynamic Customer creation if text typed
    if cust_name_input:
        cust = Customer.query.filter_by(company_id=cid, name=cust_name_input).first()
        if not cust:
            cust = Customer(
                company_id=cid,
                name=cust_name_input,
                company_name=f"{cust_name_input} Corp",
                email=f"contact@{cust_name_input.lower().replace(' ', '')}.com",
                city="Bengaluru",
                state="Karnataka"
            )
            db.session.add(cust)
            db.session.commit()
        customer_id = cust.id

    if not customer_id or str(customer_id) == '0' or str(customer_id) == 'None':
        cust = Customer.query.filter_by(company_id=cid).first()
        if not cust:
            cust = Customer(company_id=cid, name="Standard Client", company_name="Client Enterprise")
            db.session.add(cust)
            db.session.commit()
        customer_id = cust.id

    # Dynamic Product creation if text typed
    if prod_name_input:
        prod = Product.query.filter_by(company_id=cid, name=prod_name_input).first()
        if not prod:
            gen_sku = f"SKU-{prod_name_input[:3].upper()}-{datetime.now().strftime('%M%S')}"
            prod = Product(
                company_id=cid,
                name=prod_name_input,
                sku=gen_sku,
                category="Hardware",
                price=amount,
                cost=amount * 0.7,
                stock_quantity=100,
                min_stock_level=10
            )
            db.session.add(prod)
            db.session.commit()
        product_id = prod.id

    if not product_id or str(product_id) == '0' or str(product_id) == 'None':
        prod = Product.query.filter_by(company_id=cid).first()
        if not prod:
            prod = Product(
                company_id=cid,
                name="Business Solution Package",
                sku="SKU-GEN-001",
                category="Software",
                price=amount,
                cost=amount * 0.7,
                stock_quantity=100,
                min_stock_level=10
            )
            db.session.add(prod)
            db.session.commit()
        product_id = prod.id

    unit_price = amount / quantity if quantity > 0 else amount

    sale = Sale(
        company_id=cid,
        customer_id=int(customer_id),
        product_id=int(product_id),
        quantity=quantity,
        unit_price=unit_price,
        total_amount=amount,
        sale_date=sale_date,
        region=region
    )
    db.session.add(sale)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'sale_id': sale.id, 'total_amount': amount})
    return redirect(url_for('sales'))

@app.route('/sales/report/pdf')
def download_sales_pdf():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    company = Company.query.get(cid) or Company.query.first()

    selected_month = request.args.get('month', '').strip()

    all_sales = Sale.query.filter_by(company_id=cid).order_by(Sale.sale_date.desc()).all()

    if selected_month and selected_month.lower() != 'all':
        filtered_sales = []
        for s in all_sales:
            if s.sale_date:
                m_str1 = s.sale_date.strftime('%Y-%m')
                m_str2 = s.sale_date.strftime('%B %Y').lower()
                if selected_month == m_str1 or selected_month.lower() in m_str2 or m_str2 in selected_month.lower():
                    filtered_sales.append(s)
        sales_list = filtered_sales if filtered_sales else all_sales
        report_title = f"SALES REPORT - {selected_month.upper()}"
    else:
        sales_list = all_sales
        report_title = "SALES & REVENUE REPORT"

    sales_ml = predict_sales(cid)

    # Monthly breakdown
    monthly_map = {}
    for s in all_sales:
        if s.sale_date:
            m_key = s.sale_date.strftime('%B %Y')
            m_sort = s.sale_date.strftime('%Y-%m')
            if m_key not in monthly_map:
                monthly_map[m_key] = {'month': m_key, 'total': 0.0, 'count': 0, 'sort_key': m_sort}
            monthly_map[m_key]['total'] += s.total_amount
            monthly_map[m_key]['count'] += 1

    monthly_breakdown = sorted(monthly_map.values(), key=lambda x: x['sort_key'], reverse=True)

    month_suffix = selected_month.replace(' ', '_').replace('-', '_') if selected_month else 'All'
    pdf_filename = f"NexusAI_Sales_Report_{month_suffix}_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.abspath(os.path.join('static', 'reports', pdf_filename))

    generate_sales_report_pdf(company, sales_list, monthly_breakdown, sales_ml, pdf_path, report_title=report_title)
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

@app.route('/inventory')
def inventory():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    inv_forecast = forecast_inventory(cid)
    products = Product.query.filter_by(company_id=cid).order_by(Product.name.asc()).all()
    return render_template('inventory.html', forecast=inv_forecast[:10], products=products)

@app.route('/expenses')
def expenses():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    expense_list = Expense.query.filter_by(company_id=cid).order_by(Expense.expense_date.desc()).limit(15).all()
    exp_analysis = analyze_expenses(cid)
    return render_template('expenses.html', expenses=expense_list, analysis=exp_analysis)

@app.route('/expenses/add', methods=['POST'])
def add_expense():
    if not is_logged_in():
        if request.is_json:
            return jsonify({'error': 'Unauthorized'}), 401
        return redirect(url_for('login'))

    cid = get_cid()
    data = request.get_json(silent=True) or request.form

    category = data.get('category', '').strip() or "General Operations"
    description = data.get('description', '').strip() or "Business Operational Expense"
    vendor = data.get('vendor', '').strip() or "Vendor"
    payment_method = data.get('payment_method', 'UPI').strip()

    try:
        amount = float(data.get('amount', 15000.0))
    except (ValueError, TypeError):
        amount = 15000.0

    exp_date_str = data.get('expense_date')
    if exp_date_str:
        try:
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
        except ValueError:
            exp_date = date.today()
    else:
        exp_date = date.today()

    exp = Expense(
        company_id=cid,
        category=category,
        description=description,
        amount=amount,
        vendor=vendor,
        payment_method=payment_method,
        expense_date=exp_date,
        status="Approved"
    )
    db.session.add(exp)
    db.session.commit()

    if request.is_json:
        return jsonify({'status': 'success', 'expense_id': exp.id, 'amount': amount})
    return redirect(url_for('expenses'))

@app.route('/hr')
def hr():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    employees = Employee.query.filter_by(company_id=cid).order_by(Employee.first_name.asc()).limit(10).all()
    leaves = LeaveRequest.query.filter_by(company_id=cid).order_by(LeaveRequest.created_at.desc()).limit(10).all()
    return render_template('hr.html', employees=employees, leaves=leaves)

@app.route('/tasks')
def tasks():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    task_list = Task.query.filter_by(company_id=cid).order_by(Task.due_date.asc()).limit(10).all()
    employees = Employee.query.filter_by(company_id=cid).order_by(Employee.first_name.asc()).all()
    return render_template('tasks.html', tasks=task_list, employees=employees)

@app.route('/notifications')
def notifications():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    notification_list = Notification.query.filter_by(company_id=cid).order_by(Notification.created_at.desc()).limit(10).all()
    return render_template('notifications.html', notifications=notification_list)

@app.route('/settings')
def settings():
    if not is_logged_in():
        return redirect(url_for('login'))
    cid = get_cid()
    company = Company.query.get(cid) or Company.query.first()
    return render_template('settings.html', company=company)


# ==========================================
# 2. REST API ENDPOINTS
# ==========================================

@app.route('/api/auth/demo-login', methods=['POST'])
def api_demo_login():
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User.query.first()
    if user:
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['company_id'] = 1 # Force demo company id 1
        return jsonify({'status': 'success', 'redirect': url_for('dashboard')})
    return jsonify({'status': 'error', 'message': 'Demo account not found. Run seed script first.'}), 404

def group_chats_by_date(chats):
    today = date.today()
    yesterday = today - timedelta(days=1)

    grouped = {
        'Today': [],
        'Yesterday': [],
        'Older': []
    }

    for chat in chats:
        updated_date = chat.updated_at.date() if chat.updated_at else chat.created_at.date()
        chat_dict = {
            'id': chat.id,
            'title': chat.title or 'New Conversation',
            'created_at': chat.created_at.isoformat(),
            'updated_at': chat.updated_at.isoformat() if chat.updated_at else chat.created_at.isoformat(),
            'message_count': len(chat.messages)
        }
        if updated_date == today:
            grouped['Today'].append(chat_dict)
        elif updated_date == yesterday:
            grouped['Yesterday'].append(chat_dict)
        else:
            grouped['Older'].append(chat_dict)

    return grouped

@app.route('/api/ai/chats', methods=['GET'])
def get_user_chats():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session.get('user_id')
    chats = AdvisorChat.query.filter_by(user_id=user_id).order_by(AdvisorChat.updated_at.desc()).all()
    grouped = group_chats_by_date(chats)
    return jsonify({
        'status': 'success',
        'chats': grouped,
        'all_chats': [{
            'id': c.id,
            'title': c.title or 'New Conversation',
            'updated_at': c.updated_at.isoformat() if c.updated_at else c.created_at.isoformat()
        } for c in chats]
    })

@app.route('/api/ai/chats/new', methods=['POST'])
def create_new_chat():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session.get('user_id')
    cid = get_cid()
    new_chat = AdvisorChat(user_id=user_id, company_id=cid, title='New Conversation')
    db.session.add(new_chat)
    db.session.commit()
    return jsonify({
        'status': 'success',
        'chat': {
            'id': new_chat.id,
            'title': new_chat.title,
            'created_at': new_chat.created_at.isoformat(),
            'messages': []
        }
    })

@app.route('/api/ai/chats/<int:chat_id>', methods=['GET'])
def get_chat_details(chat_id):
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session.get('user_id')
    chat = AdvisorChat.query.filter_by(id=chat_id, user_id=user_id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404

    messages = []
    for msg in chat.messages:
        messages.append({
            'id': msg.id,
            'sender': msg.sender,
            'content': msg.content,
            'extra_data': json.loads(msg.extra_data) if msg.extra_data else None,
            'created_at': msg.created_at.isoformat()
        })

    return jsonify({
        'status': 'success',
        'chat': {
            'id': chat.id,
            'title': chat.title,
            'created_at': chat.created_at.isoformat(),
            'messages': messages
        }
    })

@app.route('/api/ai/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session.get('user_id')
    chat = AdvisorChat.query.filter_by(id=chat_id, user_id=user_id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404

    db.session.delete(chat)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Chat deleted successfully'})

@app.route('/api/ai/chats/<int:chat_id>/rename', methods=['POST'])
def rename_chat(chat_id):
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session.get('user_id')
    chat = AdvisorChat.query.filter_by(id=chat_id, user_id=user_id).first()
    if not chat:
        return jsonify({'error': 'Chat not found'}), 404

    data = request.get_json() or {}
    new_title = data.get('title', '').strip()
    if not new_title:
        return jsonify({'error': 'Title string is required'}), 400

    chat.title = new_title
    chat.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'success', 'title': chat.title})

@app.route('/api/ai/query', methods=['POST'])
def api_ai_query():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401

    query = ""
    chat_id = None
    file_data = None
    attachment_meta = None
    is_voice = False

    # Handle JSON payload (which may include base64 file) or Multipart Form Data
    if request.is_json:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        chat_id = data.get('chat_id')
        is_voice = data.get('is_voice', False)
        incoming_file = data.get('file') # Expected dict: {"name": ..., "mime_type": ..., "data": ...}
        if incoming_file and isinstance(incoming_file, dict):
            fname = werkzeug.utils.secure_filename(incoming_file.get('name', 'file'))
            mime_type = incoming_file.get('mime_type', 'application/octet-stream')
            b64_data = incoming_file.get('data', '')

            # Extract ext
            ext = os.path.splitext(fname)[1].lower()

            # Security check: Blacklist executables
            blacklisted = ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.py', '.js', '.vbs', '.msi', '.jar', '.dll', '.scr', '.php', '.rb', '.pl']
            if ext in blacklisted:
                return jsonify({'error': 'Security Warning: Executable and script files are strictly prohibited.'}), 400

            # File size check (max 10MB for base64 ~ 13.3MB b64 len)
            if len(b64_data) > 14 * 1024 * 1024:
                return jsonify({'error': 'File size exceeds maximum 10MB limit.'}), 400

            # Whitelist supported MIME/Extensions
            allowed_imgs = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
            allowed_docs = ['.pdf', '.txt', '.csv']

            if ext in allowed_imgs or mime_type.startswith('image/'):
                file_data = {'mime_type': mime_type or 'image/png', 'data': b64_data}
                attachment_meta = {'name': fname, 'mime_type': mime_type, 'type': 'image'}
            elif ext in allowed_docs or mime_type in ['application/pdf', 'text/plain', 'text/csv']:
                # For plain text / csv, decode text into query prompt if helpful
                if ext in ['.txt', '.csv']:
                    try:
                        raw_bytes = base64.b64decode(b64_data)
                        text_content = raw_bytes.decode('utf-8', errors='ignore')
                        query = f"{query}\n\n[Attached File Content - {fname}]:\n{text_content[:8000]}"
                    except Exception:
                        pass
                file_data = {'mime_type': mime_type or 'application/pdf', 'data': b64_data}
                attachment_meta = {'name': fname, 'mime_type': mime_type, 'type': 'doc'}
            else:
                return jsonify({'error': "Sorry, this file type isn't currently supported."}), 400

    else: # Form Data with file upload
        query = request.form.get('query', '').strip()
        chat_id = request.form.get('chat_id')
        if 'file' in request.files:
            file_obj = request.files['file']
            if file_obj and file_obj.filename:
                fname = werkzeug.utils.secure_filename(file_obj.filename)
                ext = os.path.splitext(fname)[1].lower()

                blacklisted = ['.exe', '.bat', '.cmd', '.ps1', '.sh', '.py', '.js', '.vbs', '.msi', '.jar', '.dll', '.scr', '.php', '.rb', '.pl']
                if ext in blacklisted:
                    return jsonify({'error': 'Security Warning: Executable and script files are strictly prohibited.'}), 400

                file_bytes = file_obj.read()
                if len(file_bytes) > 10 * 1024 * 1024:
                    return jsonify({'error': 'File size exceeds maximum 10MB limit.'}), 400

                mime_type = file_obj.content_type or 'application/octet-stream'
                b64_str = base64.b64encode(file_bytes).decode('utf-8')

                allowed_imgs = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
                allowed_docs = ['.pdf', '.txt', '.csv']

                if ext in allowed_imgs or mime_type.startswith('image/'):
                    file_data = {'mime_type': mime_type, 'data': b64_str}
                    attachment_meta = {'name': fname, 'mime_type': mime_type, 'type': 'image'}
                elif ext in allowed_docs or mime_type in ['application/pdf', 'text/plain', 'text/csv']:
                    if ext in ['.txt', '.csv']:
                        try:
                            text_content = file_bytes.decode('utf-8', errors='ignore')
                            query = f"{query}\n\n[Attached File Content - {fname}]:\n{text_content[:8000]}"
                        except Exception:
                            pass
                    file_data = {'mime_type': mime_type, 'data': b64_str}
                    attachment_meta = {'name': fname, 'mime_type': mime_type, 'type': 'doc'}
                else:
                    return jsonify({'error': "Sorry, this file type isn't currently supported."}), 400

    if not query and not file_data:
        return jsonify({'error': 'Query string or valid file attachment is required.'}), 400

    if not query:
        query = "Describe and analyze the attached file."

    user_id = session.get('user_id')
    cid = get_cid()

    # Retrieve or create chat
    chat = None
    if chat_id:
        chat = AdvisorChat.query.filter_by(id=chat_id, user_id=user_id).first()

    if not chat:
        chat = AdvisorChat(user_id=user_id, company_id=cid, title='New Conversation')
        db.session.add(chat)
        db.session.commit()

    # Reconstruct multi-turn history from DB messages for continuous context
    db_messages = AdvisorMessage.query.filter_by(chat_id=chat.id).order_by(AdvisorMessage.created_at).all()
    history = []
    for msg in db_messages:
        role = "user" if msg.sender in ["user", "human"] else "model"
        history.append({"role": role, "content": msg.content})

    # Process AI query with context history and optional multimodal file_data
    response = process_ai_query(query, company_id=cid, history=history, file_data=file_data, is_voice=is_voice)
    reply_text = response.get('reply') or response.get('insight', '')

    # Auto-generate title if default
    if chat.title == 'New Conversation' and len(db_messages) <= 1:
        new_title = generate_chat_title(query)
        if new_title:
            chat.title = new_title
            chat.updated_at = datetime.utcnow()
            db.session.commit()

    # Prepare extra_data payload for User Message (including attachment metadata)
    user_extra = {}
    if attachment_meta:
        user_extra['attachment'] = attachment_meta

    # Save User Message
    user_msg = AdvisorMessage(
        chat_id=chat.id,
        sender='user',
        content=query,
        extra_data=json.dumps(user_extra) if user_extra else None
    )
    db.session.add(user_msg)

    # Prepare extra_data payload for AI Message
    extra_payload = {}
    if response.get('action_url'):
        extra_payload['action_url'] = response.get('action_url')
        extra_payload['action_label'] = response.get('action_label')
    if response.get('email_data'):
        extra_payload['email_data'] = response.get('email_data')
    if response.get('tool_used'):
        extra_payload['tool_used'] = response.get('tool_used')

    # Save AI Message
    ai_msg = AdvisorMessage(
        chat_id=chat.id,
        sender='ai',
        content=reply_text,
        extra_data=json.dumps(extra_payload) if extra_payload else None
    )
    db.session.add(ai_msg)

    db.session.commit()

    response['chat_id'] = chat.id
    response['chat_title'] = chat.title

    return jsonify(response)

@app.route('/api/ai/priorities', methods=['GET'])
def api_ai_priorities():
    priorities = get_today_ai_priorities(get_cid())
    return jsonify({'priorities': priorities})

@app.route('/api/ai/email', methods=['POST'])
def api_ai_email():
    data = request.get_json() or {}
    target = data.get('target', '').strip()
    topic = data.get('topic', '').strip()
    context = data.get('context', '').strip()
    user_prompt = data.get('user_prompt', '').strip()
    reset_history = data.get('reset', False)

    if reset_history:
        session['email_chat_history'] = []

    history = session.get('email_chat_history', [])
    if not isinstance(history, list):
        history = []

    res = generate_email(
        target_name=target,
        topic=topic,
        context=context,
        history=history,
        user_prompt=user_prompt
    )

    user_turn = user_prompt or f"Target: {target}, Topic: {topic}, Context: {context}"
    model_turn = f"Subject: {res['subject']}\n\n{res['body']}"

    history.append({"role": "user", "content": user_turn})
    history.append({"role": "model", "content": model_turn})
    session['email_chat_history'] = history[-10:]

    return jsonify(res)

@app.route('/api/ai/summarize-meeting', methods=['POST'])
def api_summarize_meeting():
    data = request.get_json() or {}
    transcript = data.get('transcript', '').strip()
    title = data.get('title', 'Team Sync Meeting').strip()
    cid = get_cid()

    if not transcript:
        return jsonify({'error': 'Meeting transcript is required'}), 400

    res = summarize_meeting(transcript, company_id=cid)

    meeting = Meeting(
        company_id=cid,
        title=title,
        meeting_date=datetime.now(),
        transcript=transcript,
        summary=res['summary'],
        key_decisions=res['key_decisions']
    )
    db.session.add(meeting)
    db.session.commit()

    res['meeting_id'] = meeting.id
    return jsonify(res)

@app.route('/api/invoices', methods=['POST'])
def api_create_invoice():
    data = request.get_json() or {}
    customer_name = data.get('customer_name', '').strip()
    amount = float(data.get('amount', 0.0))
    description = data.get('description', 'Professional Services').strip()
    cid = get_cid()

    if not customer_name or amount <= 0:
        return jsonify({'error': 'Customer name and valid amount are required'}), 400

    res = create_invoice(customer_name, amount, description, company_id=cid)
    return jsonify(res)

@app.route('/api/invoices/<int:invoice_id>/pdf')
def api_invoice_pdf(invoice_id):
    cid = get_cid()
    inv = Invoice.query.filter_by(id=invoice_id, company_id=cid).first()
    if not inv:
        inv = Invoice.query.get_or_404(invoice_id)
    company = Company.query.get(cid) or Company.query.first() or Company()
    customer = inv.customer or Customer(name="Client", email="client@company.com")
    items = inv.items or [InvoiceItem(description="Business Services", quantity=1, unit_price=inv.subtotal, total_price=inv.subtotal)]

    pdf_filename = f"{inv.invoice_number}.pdf"
    pdf_path = os.path.join(os.getcwd(), 'data', 'invoices', pdf_filename)

    generate_invoice_pdf(inv, company, customer, items, pdf_path)
    return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)

@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    priority = data.get('priority', 'Medium')
    assigned_to = data.get('assigned_to', 'Operations')
    source = data.get('source', 'Manual')
    cid = get_cid()

    if not title:
        return jsonify({'error': 'Task title is required'}), 400

    res = create_task(title, description, assigned_to, priority, 3, source, company_id=cid)
    return jsonify(res)

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
def api_update_task_status(task_id):
    cid = get_cid()
    task = Task.query.filter_by(id=task_id, company_id=cid).first_or_404()
    data = request.get_json() or {}
    task.status = data.get('status', task.status)
    db.session.commit()
    return jsonify({'status': 'success', 'task_status': task.status})

@app.route('/api/leave-requests/<int:leave_id>/action', methods=['PUT'])
def api_leave_action(leave_id):
    cid = get_cid()
    leave = LeaveRequest.query.filter_by(id=leave_id, company_id=cid).first_or_404()
    data = request.get_json() or {}
    leave.status = data.get('status', leave.status)
    db.session.commit()
    return jsonify({'status': 'success', 'leave_status': leave.status})

@app.route('/api/notifications/read', methods=['POST'])
def api_mark_notifications_read():
    cid = get_cid()
    Notification.query.filter_by(company_id=cid, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/analytics/sales-prediction')
def api_sales_prediction():
    return jsonify(predict_sales(get_cid()))

@app.route('/api/analytics/inventory-forecast')
def api_inventory_forecast():
    return jsonify(forecast_inventory(get_cid()))

@app.route('/api/analytics/expense-analysis')
def api_expense_analysis():
    return jsonify(analyze_expenses(get_cid()))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
