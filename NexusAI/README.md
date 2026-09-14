# NexusAI - "Your AI Employee for Business"

> An AI-powered Business Operating System for Small and Medium Enterprises (SMEs).

---

## 🚀 Overview

Fragmented SaaS tools create data silos, administrative bloat, and operational inefficiencies for SMEs. **NexusAI** transforms this paradigm. Instead of giving business owners another software subscription, NexusAI acts as an **intelligent AI Employee**.

Connected directly to an SME's core database, NexusAI executes Python tools, performs machine learning predictions, generates ReportLab PDF invoices, extracts meeting action items into tasks, writes B2B emails, and manages daily operational priorities.

---

## ✨ Features

- **AI Business Advisor**: Ask real-time questions about sales, inventory, expenses, and clients. Returns structured outputs: `INSIGHT`, `EVIDENCE`, `RECOMMENDATION`, and `ACTION`.
- **"What should I focus on today?"**: Signature AI engine analyzing SQLite database state to generate dynamic daily business priorities.
- **Deterministic AI Tool Calling**: 13 predefined Python database tools (`get_today_sales`, `get_inventory`, `get_pending_invoices`, `create_invoice`, etc.) with fallback capabilities so the application never breaks.
- **Invoice PDF Generator**: ReportLab integration for generating branded PDF invoices with GST tax calculations and instant downloads.
- **Meeting Summarizer & Task Conversion**: Paste transcripts to extract summaries, key decisions, and action items, and convert them to tasks with one click.
- **ML Sales Prediction**: Scikit-Learn linear regression trained on historical monthly transactions.
- **ML Inventory Stockout Forecast**: Stockout velocity calculations, days-to-stockout warnings (`Healthy`, `Warning`, `Critical`), and automated reorder points.
- **Expense Anomaly Analyzer**: Anomaly detection and cost-reduction recommendations.
- **AI Email Writer**: Generate professional B2B payment reminders and proposals.
- **Voice Commands**: Web Speech API integration with microphone input and automatic text fallback.
- **Dark Futuristic UI**: Dark glassmorphic design system.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, Flask, SQLite (`data/nexusai.db`), SQLAlchemy, Werkzeug.
- **Frontend**: HTML5, CSS3 (Glassmorphism), Vanilla JavaScript, Jinja2 Templates, Chart.js.
- **AI / ML**: Scikit-Learn, Pandas, NumPy, Python Service Abstraction.
- **Document Generation**: ReportLab PDF.

---

## 📁 Folder Structure

```text
NexusAI/
├── app.py
├── database.py
├── models.py
├── ai.py
├── ml.py
├── utils.py
├── seed.py
├── requirements.txt
├── .env
├── .env.example
├── README.md
├── .gitignore
│
├── templates/
│   ├── layout.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── ai.html
│   ├── meetings.html
│   ├── invoices.html
│   ├── emails.html
│   ├── customers.html
│   ├── sales.html
│   ├── inventory.html
│   ├── expenses.html
│   ├── hr.html
│   ├── tasks.html
│   ├── notifications.html
│   └── settings.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       └── app.js
│
└── data/
    ├── nexusai.db
    └── invoices/
```

---

## ⚙️ Quick Start Guide

### 1. Prerequisites
- Python 3.11 or higher
- `pip`

### 2. Environment Setup
```bash
python -m venv venv
```

Windows:
```powershell
venv\Scripts\activate
```

Install Dependencies:
```bash
pip install -r requirements.txt
```

### 3. Database Seeding
Populate the SQLite database with 25 employees, 50 customers, 15 products, 100+ sales, 20 invoices, expenses, meetings, tasks, and notifications:
```bash
python seed.py
```

### 4. Run the Application
```bash
python app.py
```

Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 🔑 Demo Account Credentials

Click **"Instant Hackathon Demo Login"** on the login page or use:
- **Email**: `admin@nexusai.com`
- **Password**: `password123`

---

## 🏆 Hackathon Demo Flow

1. Open `http://127.0.0.1:5000` and click **"Launch Instant Demo"**.
2. View the **OS Dashboard** metrics, sales trend graph, and **"What should I focus on today?"** priority list.
3. Open **AI Business Advisor** (`/ai`) and ask:
   > *"Why did sales decrease in North India?"*
   > AI queries SQLite and returns INSIGHT, EVIDENCE, RECOMMENDATION, and ACTION detailing the 18% dip and stockout causes.
4. Prompt AI:
   > *"Create invoice for ABC Technologies for ₹25,000 for website development."*
   > AI calls `create_invoice()` tool, generates ReportLab PDF, and offers download link.
5. Click **"Download PDF"** to inspect the generated PDF invoice.
6. Open **Meeting Summarizer** (`/meetings`), paste notes, click **"Summarize & Extract Action Items"**, then click **"Convert Action Items into Tasks"**.
7. View **Tasks Board** (`/tasks`) to verify converted action items.
8. Open **Inventory Forecast** (`/inventory`) to see stockout velocity and critical alerts for Dell Inspiron & Server Racks.
