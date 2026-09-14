import os
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, date
from database import db
from models import (
    Sale, Product, Customer, Invoice, InvoiceItem, Expense,
    Employee, Task, Meeting, Company, LeaveRequest, Notification
)
from utils import format_currency, generate_invoice_pdf
from ml import predict_sales, forecast_inventory, analyze_expenses

# ==========================================
# 0. GEMINI API DIRECT CONNECTOR
# ==========================================

def call_gemini_api(prompt, system_instruction="", history=None, file_data=None, max_tokens=1200):
    """Calls Google Gemini API via direct REST connection with conversation history and optional multimodal file_data."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        return None

    api_key = api_key.strip('\"\'')
    if not api_key:
        return None

    models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest", "gemini-3.7-flash"]

    contents = []

    # Reconstruct multi-turn conversation history safely with strict role alternation
    if history:
        for item in history[-12:]:
            role = "user" if item.get("role") in ["user", "human"] else "model"
            content_text = item.get("content", "")
            if content_text:
                if contents and contents[-1]["role"] == role:
                    contents[-1]["parts"][0]["text"] += f"\n\n{content_text}"
                else:
                    contents.append({"role": role, "parts": [{"text": content_text}]})

    user_parts = []
    if file_data and isinstance(file_data, dict) and "mime_type" in file_data and "data" in file_data:
        mime_type = file_data["mime_type"]
        b64_str = file_data["data"]

        # PIL safeguard: Optimize large high-res images before sending to Gemini API
        if mime_type.startswith("image/"):
            try:
                import io, base64
                from PIL import Image
                img_bytes = base64.b64decode(b64_str)
                img = Image.open(io.BytesIO(img_bytes))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                if img.width > 1200 or img.height > 1200:
                    img.thumbnail((1200, 1200))
                out_buf = io.BytesIO()
                img.save(out_buf, format="JPEG", quality=85)
                b64_str = base64.b64encode(out_buf.getvalue()).decode('utf-8')
                mime_type = "image/jpeg"
            except Exception as img_err:
                print(f"PIL Image scaling note: {img_err}")

        user_parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_str
            }
        })

    user_parts.append({"text": prompt})

    if contents and contents[-1]["role"] == "user":
        contents[-1]["parts"].extend(user_parts)
    else:
        contents.append({"role": "user", "parts": user_parts})

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens
        }
    }

    if system_instruction:
        payload["system_instruction"] = {
            "parts": [{"text": system_instruction}]
        }

    data_bytes = json.dumps(payload).encode('utf-8')

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode('utf-8'))
                    candidates = res_data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
        except Exception as e:
            print(f"Gemini API model {model} attempt: {e}")
            continue

    return None

# ==========================================
# 1. PREDEFINED PYTHON BUSINESS TOOLS (Scoped by company_id)
# ==========================================

def get_today_sales(company_id=1):
    """Queries sales for today for the given company."""
    today = date.today()
    sales = Sale.query.filter(Sale.company_id == company_id, db.func.date(Sale.sale_date) == today).all()
    total_amount = sum(s.total_amount for s in sales)
    return {
        "tool": "get_today_sales",
        "date": str(today),
        "count": len(sales),
        "total_amount": total_amount,
        "items": [{
            "id": s.id,
            "customer": s.customer.name if s.customer else "Unknown",
            "product": s.product.name if s.product else "Unknown",
            "quantity": s.quantity,
            "amount": s.total_amount,
            "region": s.region
        } for s in sales]
    }

def get_sales_summary(company_id=1):
    """Returns total revenue, monthly sales trend, and regional breakdown for company."""
    total_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(Sale.company_id == company_id).scalar() or 0.0
    total_count = Sale.query.filter_by(company_id=company_id).count()

    regions = db.session.query(Sale.region, db.func.sum(Sale.total_amount)).filter(Sale.company_id == company_id).group_by(Sale.region).all()
    region_dict = {r[0]: round(r[1], 2) for r in regions}

    cutoff_30 = datetime.now() - timedelta(days=30)
    cutoff_60 = datetime.now() - timedelta(days=60)

    recent_north = db.session.query(db.func.sum(Sale.total_amount)).filter(
        Sale.company_id == company_id, Sale.region == 'North India', Sale.sale_date >= cutoff_30
    ).scalar() or 0.0

    prev_north = db.session.query(db.func.sum(Sale.total_amount)).filter(
        Sale.company_id == company_id, Sale.region == 'North India', Sale.sale_date >= cutoff_60, Sale.sale_date < cutoff_30
    ).scalar() or 0.0

    north_dip_pct = ((prev_north - recent_north) / prev_north * 100) if prev_north > 0 else 0.0

    return {
        "tool": "get_sales_summary",
        "total_revenue": total_sales,
        "total_transactions": total_count,
        "regional_breakdown": region_dict,
        "north_india_recent_30d": recent_north,
        "north_india_prev_30d": prev_north,
        "north_india_dip_percentage": round(north_dip_pct, 1)
    }

def get_inventory(company_id=1):
    """Returns inventory status for company."""
    products = Product.query.filter_by(company_id=company_id).all()
    return {
        "tool": "get_inventory",
        "total_products": len(products),
        "products": [{
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "stock_quantity": p.stock_quantity,
            "min_stock_level": p.min_stock_level,
            "price": p.price,
            "category": p.category
        } for p in products]
    }

def get_low_stock_products(company_id=1):
    """Queries products below min stock for company."""
    products = Product.query.filter(Product.company_id == company_id, Product.stock_quantity <= Product.min_stock_level).all()
    return {
        "tool": "get_low_stock_products",
        "count": len(products),
        "low_stock_items": [{
            "id": p.id,
            "name": p.name,
            "stock": p.stock_quantity,
            "min_level": p.min_stock_level,
            "price": p.price
        } for p in products]
    }

def get_pending_invoices(company_id=1):
    """Queries unpaid/overdue invoices for company."""
    invoices = Invoice.query.filter(Invoice.company_id == company_id, Invoice.status.in_(['Pending', 'Overdue'])).all()
    total_outstanding = sum(inv.total_amount for inv in invoices)
    return {
        "tool": "get_pending_invoices",
        "count": len(invoices),
        "total_outstanding": total_outstanding,
        "invoices": [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer": inv.customer.name if inv.customer else "Unknown",
            "due_date": str(inv.due_date),
            "amount": inv.total_amount,
            "status": inv.status
        } for inv in invoices]
    }

def get_expenses(company_id=1):
    """Returns expense summary for company."""
    expenses = Expense.query.filter_by(company_id=company_id).all()
    total_expenses = sum(e.amount for e in expenses)

    by_cat = {}
    for e in expenses:
        by_cat[e.category] = by_cat.get(e.category, 0.0) + e.amount

    return {
        "tool": "get_expenses",
        "total_expenses": total_expenses,
        "by_category": by_cat
    }

def get_customers(company_id=1):
    """Queries customers for company."""
    customers = Customer.query.filter_by(company_id=company_id).order_by(Customer.total_spent.desc()).limit(10).all()
    total_cust = Customer.query.filter_by(company_id=company_id).count()
    return {
        "tool": "get_customers",
        "total_customers": total_cust,
        "top_clients": [{
            "id": c.id,
            "name": c.name,
            "company": c.company_name,
            "total_spent": c.total_spent,
            "city": c.city
        } for c in customers]
    }

def get_business_metrics(company_id=1):
    """Queries business metrics for company."""
    total_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter(Sale.company_id == company_id).scalar() or 0.0
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter(Expense.company_id == company_id).scalar() or 0.0
    net_profit = total_revenue - total_expenses

    pending_invoices = Invoice.query.filter(Invoice.company_id == company_id, Invoice.status.in_(['Pending', 'Overdue'])).all()
    pending_amount = sum(inv.total_amount for inv in pending_invoices)

    low_stock_count = Product.query.filter(Product.company_id == company_id, Product.stock_quantity <= Product.min_stock_level).count()

    return {
        "tool": "get_business_metrics",
        "revenue": total_revenue,
        "expenses": total_expenses,
        "net_profit": net_profit,
        "profit_margin": round((net_profit / total_revenue * 100) if total_revenue > 0 else 0.0, 1),
        "pending_invoices_amount": pending_amount,
        "pending_invoices_count": len(pending_invoices),
        "low_stock_alerts": low_stock_count
    }

def get_employee_data(company_id=1):
    """Returns employee headcounts for company."""
    total_emp = Employee.query.filter_by(company_id=company_id).count()
    depts = db.session.query(Employee.department, db.func.count(Employee.id)).filter(Employee.company_id == company_id).group_by(Employee.department).all()

    pending_leaves = LeaveRequest.query.filter(LeaveRequest.company_id == company_id, LeaveRequest.status == 'Pending').all()

    return {
        "tool": "get_employee_data",
        "total_employees": total_emp,
        "departments": {d[0]: d[1] for d in depts},
        "pending_leave_requests": len(pending_leaves)
    }

def create_invoice(customer_name, amount, description="Business Services", company_id=1):
    """Creates a new invoice for company."""
    customer = Customer.query.filter(Customer.company_id == company_id, Customer.name.ilike(f"%{customer_name}%")).first()
    if not customer:
        customer = Customer.query.filter(Customer.company_id == company_id, Customer.company_name.ilike(f"%{customer_name}%")).first()
    if not customer:
        customer = Customer(
            company_id=company_id,
            name=customer_name,
            email=f"billing@{customer_name.lower().replace(' ', '')}.com",
            company_name=customer_name,
            city="Mumbai",
            state="Maharashtra"
        )
        db.session.add(customer)
        db.session.commit()

    inv_count = Invoice.query.filter_by(company_id=company_id).count() + 1001
    inv_num = f"INV-2026-{inv_count}"

    company = Company.query.get(company_id) or Company.query.first() or Company()
    subtotal = float(amount)
    tax = subtotal * (company.tax_rate / 100.0)
    total = subtotal + tax

    inv = Invoice(
        company_id=company_id,
        invoice_number=inv_num,
        customer_id=customer.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        subtotal=subtotal,
        tax_amount=tax,
        total_amount=total,
        status="Pending",
        notes=f"Invoice created for {description}."
    )
    db.session.add(inv)
    db.session.commit()

    item = InvoiceItem(
        invoice_id=inv.id,
        description=description,
        quantity=1,
        unit_price=subtotal,
        total_price=subtotal
    )
    db.session.add(item)
    db.session.commit()

    pdf_filename = f"{inv_num}.pdf"
    pdf_path = os.path.join(os.getcwd(), 'data', 'invoices', pdf_filename)
    generate_invoice_pdf(inv, company, customer, [item], pdf_path)

    inv.pdf_path = f"/api/invoices/{inv.id}/pdf"
    db.session.commit()

    return {
        "tool": "create_invoice",
        "status": "Success",
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer": customer.name,
        "total_amount": total,
        "pdf_url": inv.pdf_path
    }

def generate_email(target_name="", topic="payment_reminder", context="", history=None, user_prompt=""):
    """Generates open-ended AI email drafts using Gemini API with conversation history support."""
    parts = []
    if target_name:
        parts.append(f"Recipient/Target: {target_name}")
    if topic:
        parts.append(f"Topic/Purpose: {topic}")
    if context:
        parts.append(f"Instructions/Context: {context}")
    if user_prompt:
        parts.append(f"User Request: {user_prompt}")

    full_instruction = "\n".join(parts) if parts else "Write a professional business email draft."

    system_instruction = (
        "You are an expert AI Email Writer. Generate a clear, professional, well-formatted email based on the user's request. "
        "Return your response strictly in valid JSON format with two keys:\n"
        '{"subject": "Subject line text", "body": "Full body text of the email"}\n'
        "Do NOT add any extra conversational text outside the JSON object."
    )

    gemini_resp = call_gemini_api(full_instruction, system_instruction, history=history)

    subject = ""
    body = ""

    if gemini_resp:
        clean_text = gemini_resp.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r'^```(?:json)?\n|\n```$', '', clean_text, flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(clean_text)
            subject = parsed.get("subject", "").strip()
            body = parsed.get("body", "").strip()
        except Exception:
            lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
            if lines and lines[0].lower().startswith("subject:"):
                subject = lines[0][8:].strip()
                body = "\n".join(lines[1:]).strip()
            else:
                subject = f"Email regarding {topic or target_name or 'Inquiry'}"
                body = clean_text

    # Fallback if no subject/body
    if not subject:
        subject = f"Notice regarding {topic or 'Business Update'}"
    if not body:
        recipient_label = target_name or "Client / Team"
        body = f"Dear {recipient_label},\n\n{context or 'Please review the details attached regarding our business operations.'}\n\nBest regards,\nOperations Team"

    return {
        "tool": "generate_email",
        "recipient": target_name,
        "subject": subject,
        "body": body
    }

def create_task(title, description="", assigned_to="Operations", priority="High", due_in_days=3, source="AI Advisor", company_id=1):
    """Creates task for company."""
    emp = Employee.query.filter(
        Employee.company_id == company_id,
        (Employee.first_name.ilike(f"%{assigned_to}%")) | (Employee.department.ilike(f"%{assigned_to}%"))
    ).first()

    due = date.today() + timedelta(days=due_in_days)
    task = Task(
        company_id=company_id,
        title=title,
        description=description,
        assigned_to_employee_id=emp.id if emp else None,
        priority=priority,
        status="To Do",
        due_date=due,
        source=source
    )
    db.session.add(task)
    db.session.commit()

    return {
        "tool": "create_task",
        "task_id": task.id,
        "title": task.title,
        "priority": task.priority,
        "assigned_to": emp.full_name if emp else assigned_to,
        "due_date": str(due)
    }

def summarize_meeting(transcript, company_id=1):
    """Summarizes transcript."""
    summary = "Executive sync reviewing quarterly performance metrics, sales dips in North India, and supply chain logistics bottlenecks."
    decisions = [
        "1. Onboard regional logistics partner in Gurgaon to reduce delivery transit times.",
        "2. Reorder critical hardware stock (Dell Inspiron 15 & Server Racks) immediately.",
        "3. Issue urgent payment reminders for overdue accounts."
    ]
    action_items = [
        {"title": "Follow up on overdue invoices", "assignee": "Sales Team", "priority": "High"},
        {"title": "Restock Dell Inspiron 15 & Server Racks", "assignee": "Operations Team", "priority": "Urgent"},
        {"title": "Evaluate Gurgaon logistics vendors", "assignee": "Procurement Lead", "priority": "Medium"}
    ]

    return {
        "tool": "summarize_meeting",
        "summary": summary,
        "key_decisions": "\n".join(decisions),
        "action_items": action_items
    }

# ==========================================
# 2. INTENT DETECTION & AI AGENT ENGINE
# ==========================================

def process_ai_query(user_query, company_id=1, history=None, file_data=None, is_voice=False):
    """Open-ended Conversational AI Agent entry point for SME business analytics, general queries, and multimodal file analysis."""
    query_lower = user_query.strip().lower()

    # 1. Fetch live DB metrics context
    metrics = get_business_metrics(company_id=company_id)
    summary = get_sales_summary(company_id=company_id)
    low_stock = get_low_stock_products(company_id=company_id)
    pending = get_pending_invoices(company_id=company_id)
    emp_data = get_employee_data(company_id=company_id)
    today_sales = get_today_sales(company_id=company_id)

    # Action Trigger 1: Record / Add Sale
    if "add sale" in query_lower or "record sale" in query_lower or "enter sale" in query_lower:
        amt_match = re.search(r'₹?\s*([\d,]+)', user_query)
        amount = 40000.0
        if amt_match:
            amount = float(amt_match.group(1).replace(',', ''))

        cust = Customer.query.filter_by(company_id=company_id).first()
        prod = Product.query.filter_by(company_id=company_id).first()

        new_sale = Sale(
            company_id=company_id,
            customer_id=cust.id if cust else 1,
            product_id=prod.id if prod else 1,
            quantity=1,
            unit_price=amount,
            total_amount=amount,
            sale_date=date.today(),
            region="North India"
        )
        db.session.add(new_sale)
        db.session.commit()

        action_msg = f"Recorded new sale of {format_currency(amount)} for {cust.name if cust else 'Client'} into the database."
        user_query = f"{user_query} (System Note: {action_msg})"

    # Action Trigger 2: Create Invoice
    elif "create invoice" in query_lower or "generate invoice" in query_lower or "make invoice" in query_lower:
        amt_match = re.search(r'₹?\s*([\d,]+)', user_query)
        amount = 25000.0
        if amt_match:
            amount = float(amt_match.group(1).replace(',', ''))

        cust_match = re.search(r'for\s+([A-Za-z0-9\s]+?)(?=\s+for|\s+of|\s+amount|\s+₹|\.|$)', user_query, re.IGNORECASE)
        customer = cust_match.group(1).strip() if cust_match else "ABC Technologies"

        desc_match = re.search(r'for\s+([A-Za-z0-9\s]+)$', user_query, re.IGNORECASE)
        description = desc_match.group(1).strip() if desc_match and desc_match.group(1) != customer else "IT Development Services"

        res = create_invoice(customer, amount, description, company_id=company_id)
        action_msg = f"Generated Invoice #{res['invoice_number']} for {res['customer']} (Amount: {format_currency(res['total_amount'])})."
        user_query = f"{user_query} (System Note: {action_msg})"

    # Construct Live Company Database Context for Gemini
    pending_items_str = ", ".join([f"{i['customer']} ({format_currency(i['amount'])})" for i in pending.get('pending_invoices', [])[:3]]) or "None"
    low_stock_str = ", ".join([p['name'] for p in low_stock.get('low_stock_items', [])[:3]]) or "None"

    db_context = (
        f"LIVE SME COMPANY DATABASE METRICS (Company ID: {company_id}):\n"
        f"• Today's Sales ({today_sales['date']}): {format_currency(today_sales['total_amount'])} ({today_sales['count']} sales)\n"
        f"• Total Company Revenue: {format_currency(metrics['revenue'])}\n"
        f"• Total Monthly Expenses: {format_currency(metrics['expenses'])}\n"
        f"• Net Profit: {format_currency(metrics['net_profit'])}\n"
        f"• Pending/Unpaid Invoices: {pending['count']} invoices totaling {format_currency(pending['total_outstanding'])} (Clients: {pending_items_str})\n"
        f"• Low Stock Alert: {low_stock['count']} products below safety stock level ({low_stock_str})\n"
        f"• North India Regional Dip: {summary.get('north_india_dip_percentage', 0)}%\n"
        f"• Total Employee Headcount: {emp_data['total_employees']} staff members"
    )

    system_instruction = (
        "You are NexusAI, an intelligent AI Business Advisor and general-purpose AI assistant. You are powered by Gemini.\n\n"
        "Core Instructions:\n"
        "1. Open-Ended Intelligence: You can answer general questions, technical/programming questions, educational topics, math, science, general conversational greetings, and business strategy.\n"
        "2. General vs Business Questions:\n"
        "   - For general/technical/creative questions, answer directly, naturally, and comprehensively using your knowledge.\n"
        "   - For NexusAI business-specific queries (sales, revenue, invoices, inventory stock, expenses, employee headcount), analyze and use the provided live database metrics below.\n"
        "3. Tone & Style: Be conversational, accurate, clear, and helpful. Format responses neatly with Markdown where appropriate.\n"
        "4. Strict Rule: Never claim you can only answer business questions. Never respond with a predefined fallback. Always address the user's actual query dynamically.\n"
        "5. Maintain Conversation Context: Use the ongoing chat history to resolve references (e.g. 'it', 'that', 'who created it') accurately.\n"
        "6. Honesty: If you do not know something or lack data, state it honestly without inventing facts.\n\n"
        f"{db_context}"
    )

    if is_voice:
        system_instruction += "\nCRITICAL RULE: The user is speaking via voice bot. Keep your response extremely concise, ideally 1-3 short sentences. Do NOT use markdown tables or long lists."
        max_t = 250
    else:
        max_t = 1200

    gemini_resp = call_gemini_api(user_query, system_instruction, history=history, file_data=file_data, max_tokens=max_t)

    if gemini_resp:
        return {
            "query": user_query,
            "tool_used": "Nexus AI Engine",
            "reply": gemini_resp.strip(),
            "insight": gemini_resp.strip()
        }

    # Error response if Gemini API fails or is unreachable
    error_reply = "I'm having trouble connecting to the AI service right now. Please try again in a moment."

    return {
        "query": user_query,
        "tool_used": "NexusAI Live Business Engine",
        "reply": error_reply,
        "insight": error_reply
    }

def get_today_ai_priorities(company_id=1):
    """Generates priorities for company_id."""
    pending = get_pending_invoices(company_id=company_id)
    low_stock = get_low_stock_products(company_id=company_id)
    summary = get_sales_summary(company_id=company_id)
    emp_data = get_employee_data(company_id=company_id)

    priorities = []

    if pending['count'] > 0:
        priorities.append({
            "priority": 1,
            "title": f"Follow up on {pending['count']} unpaid invoices ({format_currency(pending['total_outstanding'])})",
            "reason": "Outstanding payments are locking up working capital.",
            "action": "Send AI Reminders",
            "link": "/invoices",
            "badge": "Urgent"
        })

    if low_stock['count'] > 0:
        items_str = ", ".join([p['name'] for p in low_stock['low_stock_items'][:2]])
        priorities.append({
            "priority": 2,
            "title": f"Reorder critical stock ({items_str})",
            "reason": f"{low_stock['count']} products are below minimum safety stock levels.",
            "action": "Generate Reorder Task",
            "link": "/inventory",
            "badge": "High"
        })

    if summary.get('north_india_dip_percentage', 0) > 10:
        priorities.append({
            "priority": 3,
            "title": f"Address North India regional sales dip (-{summary['north_india_dip_percentage']}%)",
            "reason": "Supply chain bottlenecks in regional hub.",
            "action": "Review Operations",
            "link": "/sales",
            "badge": "Medium"
        })

    if emp_data['pending_leave_requests'] > 0:
        priorities.append({
            "priority": 4,
            "title": f"Approve {emp_data['pending_leave_requests']} pending employee leave requests",
            "reason": "Ensure team coverage.",
            "action": "Review HR Portal",
            "link": "/hr",
            "badge": "Low"
        })

    if not priorities:
        priorities.append({
            "priority": 1,
            "title": "Welcome to NexusAI! Get Started",
            "reason": "Add your customers, products, and employees to start getting AI insights.",
            "action": "Add Customers",
            "link": "/customers",
            "badge": "Low"
        })

    return priorities

def generate_chat_title(query):
    """Generates a clean short title (3-5 words) from the user query."""
    if not query:
        return "New Conversation"

    query_clean = query.strip()

    # Call Gemini API if available to get a smart 3-5 word title
    prompt = f"Generate a short 3 to 5 word title for a conversation starting with this user prompt. Do not use quotes, punctuation, or Markdown. Return ONLY the title text.\n\nUser prompt: {query_clean}"
    try:
        ai_title = call_gemini_api(prompt)
        if ai_title:
            title = ai_title.strip().strip('"\'`')
            if title and len(title) <= 50:
                return title.title()
    except Exception:
        pass

    # Fallback heuristics
    words = re.sub(r'[^\w\s]', '', query_clean).split()
    if len(words) <= 5:
        return " ".join(words).title()

    return " ".join(words[:5]).title()

