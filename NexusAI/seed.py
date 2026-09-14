import os
import random
from datetime import datetime, timedelta, date
from flask import Flask
from database import db, init_db
from models import (
    Company, User, Customer, Employee, Product, Inventory,
    Sale, Invoice, InvoiceItem, Expense, Meeting, Task, LeaveRequest, Notification
)

os.makedirs('data', exist_ok=True)
os.makedirs('data/invoices', exist_ok=True)

app = Flask(__name__)
db_path = os.path.abspath('data/nexusai.db').replace('\\', '/')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

def seed_database():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()

        print("Seeding NexusAI Database...")

        # 1. Company
        company = Company(
            name="Nexus Tech Solutions",
            address="102 Tech Park, Outer Ring Road, Bengaluru, Karnataka 560103",
            phone="+91 80 4123 4567",
            email="contact@nexustech.in",
            currency="INR",
            tax_rate=18.0
        )
        db.session.add(company)
        db.session.commit()

        # 2. Users (Admin Demo User)
        admin_user = User(
            username="admin",
            email="admin@nexusai.com",
            role="Admin",
            company_id=company.id
        )
        admin_user.set_password("password123")
        db.session.add(admin_user)

        demo_user = User(
            username="demo",
            email="demo@nexusai.com",
            role="CEO",
            company_id=company.id
        )
        demo_user.set_password("demo123")
        db.session.add(demo_user)
        db.session.commit()

        # 3. 25 Employees (Realistic Indian Names)
        departments_positions = [
            ("Management", "CEO"), ("Management", "COO"), ("Management", "CTO"),
            ("Sales", "Head of Sales"), ("Sales", "Senior Sales Executive"), ("Sales", "Account Executive"), ("Sales", "Sales Representative"), ("Sales", "Sales Analyst"),
            ("Engineering", "Lead Architect"), ("Engineering", "Senior Full Stack Dev"), ("Engineering", "Backend Engineer"), ("Engineering", "Frontend Engineer"), ("Engineering", "DevOps Specialist"), ("Engineering", "QA Lead"),
            ("Operations", "Operations Director"), ("Operations", "Logistics Coordinator"), ("Operations", "Inventory Manager"), ("Operations", "Procurement Officer"),
            ("HR", "HR Director"), ("HR", "Talent Acquisition Lead"), ("HR", "HR Executive"),
            ("Marketing", "Marketing Manager"), ("Marketing", "Content Strategist"), ("Marketing", "SEO Specialist"), ("Marketing", "Graphic Designer")
        ]

        employee_names = [
            ("Rajesh", "Sharma"), ("Priya", "Patel"), ("Aarav", "Kumar"), ("Sunita", "Rao"),
            ("Ananya", "Iyer"), ("Vikram", "Singh"), ("Sneha", "Verma"), ("Rohan", "Deshmukh"),
            ("Kavita", "Reddy"), ("Arjun", "Mehta"), ("Meera", "Joshi"), ("Vivek", "Gupta"),
            ("Deepak", "Nair"), ("Pooja", "Chawla"), ("Amit", "Kulkarni"), ("Neha", "Bhatia"),
            ("Siddharth", "Roy"), ("Divya", "Menon"), ("Alok", "Tiwari"), ("Ritu", "Pandey"),
            ("Manish", "Saxena"), ("Tanvi", "Agarwal"), ("Gaurav", "Shetty"), ("Swati", "Kapoor"),
            ("Karan", "Malhotra")
        ]

        employees = []
        for i, (fn, ln) in enumerate(employee_names):
            dept, pos = departments_positions[i]
            emp = Employee(
                first_name=fn,
                last_name=ln,
                email=f"{fn.lower()}.{ln.lower()}@nexustech.in",
                phone=f"+91 98765 {10000 + i}",
                department=dept,
                position=pos,
                salary=round(random.uniform(45000, 220000), -3),
                status="Active",
                hire_date=date(2022, 1, 1) + timedelta(days=random.randint(0, 800))
            )
            employees.append(emp)
            db.session.add(emp)
        db.session.commit()

        # 4. 50 Customers
        cities_states = [
            ("Mumbai", "Maharashtra"), ("Bengaluru", "Karnataka"), ("Delhi", "Delhi NCR"),
            ("Hyderabad", "Telangana"), ("Pune", "Maharashtra"), ("Chennai", "Tamil Nadu"),
            ("Ahmedabad", "Gujarat"), ("Kolkata", "West Bengal"), ("Noida", "Uttar Pradesh"),
            ("Gurugram", "Haryana")
        ]

        company_suffixes = ["Technologies", "Solutions", "Enterprises", "Infotech", "Logistics", "Services", "Global", "Systems", "Consulting", "India"]

        customers = []
        for i in range(1, 51):
            fn = random.choice(["Ramesh", "Suresh", "Geeta", "Harish", "Nikhil", "Bhavna", "Tarun", "Shalini", "Varun", "Preeti", "Sanjay", "Anil"])
            ln = random.choice(["Jain", "Shah", "Mukherjee", "Chatterjee", "Aggarwal", "Pillai", "Nambiar", "Choudhury", "Dutta", "Bose"])
            comp_name = f"{ln} {random.choice(company_suffixes)}"
            city, state = random.choice(cities_states)
            cust = Customer(
                name=f"{fn} {ln}",
                email=f"contact@{comp_name.lower().replace(' ', '')}.com",
                phone=f"+91 99887 {20000 + i}",
                company_name=comp_name,
                city=city,
                state=state,
                total_spent=0.0,
                status="Active" if i <= 42 else ("Lead" if i <= 47 else "Inactive")
            )
            customers.append(cust)
            db.session.add(cust)
        db.session.commit()

        # 5. 15 Products
        product_catalog = [
            ("Dell Inspiron 15 Laptop", "HW-DELL-15", "Hardware", 62000, 48000, 8, 15), # Low stock!
            ("Enterprise Cloud Server Rack", "HW-SRV-RACK", "Hardware", 185000, 135000, 3, 5), # Low stock!
            ("Wireless Ergonomic Mouse", "ACC-WM-01", "Accessories", 1800, 950, 12, 25), # Low stock!
            ("4K Ultra HD Monitor 27-inch", "HW-MON-27", "Hardware", 28500, 21000, 24, 10),
            ("Nexus Workplace Suite (1yr License)", "SW-NEX-01", "Software", 12500, 4000, 150, 20),
            ("Cybersecurity Audit & Firewall Package", "SRV-SEC-AUD", "Services", 95000, 35000, 50, 5),
            ("Custom Web & Mobile App Development", "SRV-DEV-CUSTOM", "Services", 250000, 110000, 30, 2),
            ("Logitech HD Conference Cam", "ACC-CAM-HD", "Accessories", 18500, 13000, 14, 8),
            ("Mechanical RGB Keyboard", "ACC-KB-MECH", "Accessories", 4200, 2600, 35, 12),
            ("Cisco Enterprise Wi-Fi Router", "HW-NET-CSCO", "Hardware", 34000, 25500, 19, 8),
            ("Cloud Database Managed Support (Monthly)", "SRV-DB-SUPP", "Services", 45000, 18000, 40, 5),
            ("ERP Systems Integration Module", "SW-ERP-MOD", "Software", 140000, 50000, 25, 5),
            ("AI Chatbot Agent License", "SW-AI-BOT", "Software", 35000, 8000, 85, 10),
            ("UPS 2KVA Uninterruptible Power Supply", "HW-UPS-2K", "Hardware", 22000, 16000, 9, 10), # Low stock!
            ("Technical SLA Priority Support Contract", "SRV-SLA-PRIO", "Services", 75000, 20000, 60, 5)
        ]

        products = []
        for name, sku, cat, price, cost, stock, min_stock in product_catalog:
            p = Product(
                name=name,
                sku=sku,
                category=cat,
                price=float(price),
                cost=float(cost),
                stock_quantity=stock,
                min_stock_level=min_stock
            )
            products.append(p)
            db.session.add(p)
        db.session.commit()

        # 6. Sales History (120+ sales across past 180 days)
        # Note: We simulate a slight dip in North India sales during the last month to support the AI demo prompt: "Why did sales decrease in North India?"
        regions = ["North India", "South India", "West India", "East India"]
        sales = []
        start_date = datetime.now() - timedelta(days=180)

        for day_offset in range(180):
            current_date = start_date + timedelta(days=day_offset)
            is_recent_month = (datetime.now() - current_date).days <= 30

            # Daily sales count
            daily_count = random.randint(0, 3)
            for _ in range(daily_count):
                cust = random.choice(customers[:40])
                prod = random.choice(products)
                region = random.choice(regions)

                # Simulate regional dip for North India in recent 30 days
                if region == "North India" and is_recent_month and random.random() < 0.6:
                    continue # Skip some North India sales to create realistic data dip!

                qty = random.randint(1, 4)
                total = prod.price * qty

                sale = Sale(
                    customer_id=cust.id,
                    product_id=prod.id,
                    quantity=qty,
                    unit_price=prod.price,
                    total_amount=total,
                    sale_date=current_date,
                    status="Completed",
                    region=region
                )
                sales.append(sale)
                cust.total_spent += total
                db.session.add(sale)

                # Inventory log
                inv_log = Inventory(
                    product_id=prod.id,
                    change_quantity=-qty,
                    reason="Customer Order Sale",
                    timestamp=current_date
                )
                db.session.add(inv_log)

        db.session.commit()

        # 7. Invoices (20 Invoices)
        invoice_statuses = ["Paid", "Paid", "Pending", "Overdue", "Paid"]
        invoices = []
        for i in range(1, 21):
            cust = random.choice(customers[:35])
            issue = date.today() - timedelta(days=random.randint(5, 60))
            due = issue + timedelta(days=30)

            # Determine status based on due date
            if due < date.today() and i % 3 == 0:
                status = "Overdue"
            elif i % 2 == 0:
                status = "Paid"
            else:
                status = "Pending"

            inv = Invoice(
                invoice_number=f"INV-2026-{1000 + i}",
                customer_id=cust.id,
                issue_date=issue,
                due_date=due,
                subtotal=0.0,
                tax_amount=0.0,
                total_amount=0.0,
                status=status,
                notes="Thank you for doing business with Nexus Tech Solutions. Payment terms: 30 days net."
            )
            db.session.add(inv)
            db.session.commit() # Get inv.id

            # Invoice items (1 to 3 items per invoice)
            subtotal = 0.0
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                p = random.choice(products)
                qty = random.randint(1, 3)
                total_p = p.price * qty
                subtotal += total_p
                item = InvoiceItem(
                    invoice_id=inv.id,
                    product_id=p.id,
                    description=p.name,
                    quantity=qty,
                    unit_price=p.price,
                    total_price=total_p
                )
                db.session.add(item)

            tax = subtotal * 0.18 # 18% GST
            inv.subtotal = subtotal
            inv.tax_amount = tax
            inv.total_amount = subtotal + tax
            db.session.commit()

        # 8. 35 Expenses over 6 months
        expense_cats = ["Marketing", "Salaries", "Operations", "Software", "Rent", "Utilities"]
        vendors = ["AWS Cloud Services", "Google Ads", "WeWork Office Space", "Microsoft 365", "Airtel Business", "Internal Payroll", "Razorpay Gateway"]

        for month_offset in range(6):
            m_date = date.today() - timedelta(days=30 * month_offset)
            # Add regular expenses
            for cat in expense_cats:
                amt = 0.0
                if cat == "Salaries":
                    amt = 185000.0
                elif cat == "Rent":
                    amt = 65000.0
                elif cat == "Software":
                    amt = 28000.0
                elif cat == "Marketing":
                    amt = 45000.0 if month_offset != 1 else 95000.0 # Anomaly spike 1 month ago!
                elif cat == "Operations":
                    amt = 32000.0
                else:
                    amt = 14000.0

                exp = Expense(
                    category=cat,
                    description=f"Monthly {cat} Payment for {m_date.strftime('%B %Y')}",
                    amount=amt,
                    expense_date=m_date - timedelta(days=random.randint(1, 25)),
                    payment_method="Bank Transfer",
                    vendor=random.choice(vendors),
                    status="Approved"
                )
                db.session.add(exp)
        db.session.commit()

        # 9. Meetings
        sample_transcript = """
Participant 1 (CEO Rajesh): Team, let me welcome everyone. We are reviewing our Q3 performance. North India sales showed a 18% drop compared to South India.
Participant 2 (Sales Lead Priya): That's correct. We faced delays in shipping Dell Inspiron laptops and Enterprise Server Racks to DelhiNCR clients due to logistics bottlenecks in Gurgaon hub.
Participant 3 (Ops Manager Rohan): We need to onboard an additional regional logistics carrier in North India by next week to prevent delivery delays.
Participant 1 (CEO Rajesh): Agreed. Priya will also follow up on the 3 overdue enterprise invoices exceeding ₹1.5 Lakhs. Rohan will initiate restocking for Dell Inspiron 15 and Server Racks immediately.
"""
        meeting1 = Meeting(
            title="Q3 Regional Sales Review & Operations Sync",
            meeting_date=datetime.now() - timedelta(days=2),
            transcript=sample_transcript,
            summary="Reviewed Q3 performance across regional hubs. Identified logistics bottlenecks causing an 18% drop in North India sales due to delayed laptop & server hardware shipments.",
            key_decisions="1. Onboard local North India logistics carrier by next week.\n2. Reorder low stock hardware items (Dell Inspiron 15 & Server Racks).\n3. Aggressively follow up on overdue invoices."
        )
        db.session.add(meeting1)
        db.session.commit()

        # 10. Tasks
        tasks_data = [
            ("Follow up on overdue invoices", "Contact ABC Technologies & Apex Solutions regarding pending payment of ₹1,45,000.", 2, "High", "To Do", date.today() + timedelta(days=2), "AI Advisor"),
            ("Reorder Dell Inspiron 15 Inventory", "Current stock level is 8 units (below min stock threshold of 15). Place order for 20 units with supplier.", 17, "Urgent", "To Do", date.today() + timedelta(days=1), "Low Stock"),
            ("Onboard North India Logistics Partner", "Evaluate 3 logistics vendors in Gurgaon to optimize supply chain delivery times.", 15, "High", "In Progress", date.today() + timedelta(days=5), "AI Meeting"),
            ("Review Q3 Marketing Campaign ROI", "Analyze Google Ads expenditure spike (₹95,000) vs lead conversion rate.", 22, "Medium", "To Do", date.today() + timedelta(days=7), "AI Advisor"),
            ("Approve Employee Annual Leave Requests", "Review pending leave applications for engineering team before sprint planning.", 19, "Low", "Completed", date.today() - timedelta(days=1), "Manual")
        ]

        for title, desc, emp_idx, prio, stat, due, src in tasks_data:
            t = Task(
                title=title,
                description=desc,
                assigned_to_employee_id=employees[emp_idx].id if emp_idx < len(employees) else employees[0].id,
                priority=prio,
                status=stat,
                due_date=due,
                source=src
            )
            db.session.add(t)
        db.session.commit()

        # 11. Leave Requests
        leave_reqs = [
            (employees[3].id, "Casual", date.today() + timedelta(days=3), date.today() + timedelta(days=5), "Family function in hometown", "Pending"),
            (employees[8].id, "Sick", date.today() - timedelta(days=4), date.today() - timedelta(days=2), "Fever and rest recommended by doctor", "Approved"),
            (employees[14].id, "Earned", date.today() + timedelta(days=10), date.today() + timedelta(days=17), "Annual vacation leave", "Pending")
        ]

        for emp_id, l_type, s_date, e_date, reason, stat in leave_reqs:
            lr = LeaveRequest(
                employee_id=emp_id,
                leave_type=l_type,
                start_date=s_date,
                end_date=e_date,
                reason=reason,
                status=stat
            )
            db.session.add(lr)
        db.session.commit()

        # 12. Notifications
        notifications = [
            ("Low Stock Alert", "Dell Inspiron 15 stock is critical (8 units left). AI recommends reordering 20 units.", "warning", "/inventory"),
            ("Overdue Invoice Alert", "Invoice INV-2026-1004 for Apex Solutions (₹85,000) is 12 days overdue.", "danger", "/invoices"),
            ("AI Business Priority", "Sales in North India dipped by 18% last month. AI generated actionable recommendations.", "ai", "/ai"),
            ("New Leave Request", "Sunita Rao submitted a casual leave request for 3 days.", "info", "/hr")
        ]

        for title, msg, n_type, link in notifications:
            n = Notification(
                title=title,
                message=msg,
                type=n_type,
                link=link
            )
            db.session.add(n)
        db.session.commit()

        print("Database successfully seeded with 25 Employees, 50 Customers, 15 Products, 100+ Sales, 20 Invoices, Expenses, Meetings & Tasks!")

if __name__ == '__main__':
    seed_database()
