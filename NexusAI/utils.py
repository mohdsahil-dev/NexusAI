import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def format_currency(amount):
    """Format numbers into Indian Rupee format (₹ X,XX,XXX.XX)."""
    if amount is None:
        return "₹0.00"
    return f"₹{amount:,.2f}"

def generate_invoice_pdf(invoice, company, customer, items, output_path):
    """
    Generates a professional PDF invoice using ReportLab.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Colors
    primary_color = colors.HexColor("#0f172a") # Dark Slate
    accent_color = colors.HexColor("#0284c7")  # Bright Blue
    light_bg = colors.HexColor("#f8fafc")
    text_dark = colors.HexColor("#334155")

    # Custom Styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=accent_color,
        fontName='Helvetica-Bold'
    )

    company_header_style = ParagraphStyle(
        'CompanyHeader',
        parent=styles['Normal'],
        fontSize=12,
        leading=15,
        textColor=primary_color,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=text_dark
    )

    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=primary_color,
        fontName='Helvetica-Bold'
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )

    # 1. Header (Company Info & Invoice Title)
    header_data = [
        [
            Paragraph(f"<b>{company.name}</b><br/>{company.address}<br/>Phone: {company.phone}<br/>Email: {company.email}", normal_style),
            Paragraph(f"<b>INVOICE</b><br/><font size=10 color='#64748b'>#{invoice.invoice_number}</font>", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[320, 220])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=15))

    # 2. Bill To & Invoice Meta
    bill_to_text = f"<b>BILL TO:</b><br/>{customer.name}<br/><b>{customer.company_name or ''}</b><br/>{customer.city}, {customer.state}<br/>Email: {customer.email}"
    meta_text = f"<b>Issue Date:</b> {invoice.issue_date.strftime('%b %d, %Y') if invoice.issue_date else 'N/A'}<br/>" \
                f"<b>Due Date:</b> {invoice.due_date.strftime('%b %d, %Y') if invoice.due_date else 'N/A'}<br/>" \
                f"<b>Status:</b> <font color='{'#16a34a' if invoice.status == 'Paid' else ('#dc2626' if invoice.status == 'Overdue' else '#d97706')}'><b>{invoice.status.upper()}</b></font>"

    info_data = [
        [Paragraph(bill_to_text, normal_style), Paragraph(meta_text, normal_style)]
    ]
    info_table = Table(info_data, colWidths=[320, 220])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    # 3. Itemized Table
    table_data = [
        [
            Paragraph("<b>Item / Description</b>", table_header_style),
            Paragraph("<b>Qty</b>", table_header_style),
            Paragraph("<b>Unit Price (₹)</b>", table_header_style),
            Paragraph("<b>Total (₹)</b>", table_header_style)
        ]
    ]

    for item in items:
        table_data.append([
            Paragraph(item.description, normal_style),
            Paragraph(str(item.quantity), normal_style),
            Paragraph(f"₹{item.unit_price:,.2f}", normal_style),
            Paragraph(f"₹{item.total_price:,.2f}", bold_style)
        ])

    items_table = Table(table_data, colWidths=[270, 50, 110, 110])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), accent_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))

    # 4. Totals Summary
    subtotal_fmt = f"₹{invoice.subtotal:,.2f}"
    tax_fmt = f"₹{invoice.tax_amount:,.2f}"
    total_fmt = f"₹{invoice.total_amount:,.2f}"

    totals_data = [
        [Paragraph("Subtotal:", normal_style), Paragraph(subtotal_fmt, normal_style)],
        [Paragraph(f"GST ({company.tax_rate:.0f}%):", normal_style), Paragraph(tax_fmt, normal_style)],
        [Paragraph("<b>Grand Total:</b>", bold_style), Paragraph(f"<b>{total_fmt}</b>", title_style)]
    ]
    totals_table = Table(totals_data, colWidths=[120, 100])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEABOVE', (0,2), (1,2), 1, primary_color),
    ]))

    wrapper_data = [
        [Paragraph(f"<b>Notes & Payment Terms:</b><br/>{invoice.notes or 'Payment due within 30 days.'}", normal_style), totals_table]
    ]
    wrapper_table = Table(wrapper_data, colWidths=[320, 220])
    wrapper_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(wrapper_table)
    story.append(Spacer(1, 30))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))
    footer_text = "NexusAI - Powered Business Operating System | Generated automatically by NexusAI Agent"
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.HexColor("#94a3b8"))
    story.append(Paragraph(footer_text, footer_style))

    doc.build(story)
    return output_path

def generate_sales_report_pdf(company, sales_list, monthly_breakdown, sales_ml, output_path, report_title="SALES & REVENUE REPORT"):
    """
    Generates a professional PDF Sales & Financial Report using ReportLab.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#0f172a")
    accent_color = colors.HexColor("#0284c7")
    light_bg = colors.HexColor("#f8fafc")
    text_dark = colors.HexColor("#334155")

    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=accent_color,
        fontName='Helvetica-Bold'
    )

    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=9, leading=12, textColor=text_dark)
    bold_style = ParagraphStyle('BoldText', parent=styles['Normal'], fontSize=9, leading=12, textColor=primary_color, fontName='Helvetica-Bold')
    header_style = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.white, fontName='Helvetica-Bold')

    # Header
    header_data = [
        [
            Paragraph(f"<b>{company.name}</b><br/>{company.address}<br/>Email: {company.email}", normal_style),
            Paragraph(f"<b>{report_title}</b><br/><font size=9 color='#64748b'>Date: {datetime.now().strftime('%b %d, %Y')}</font>", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=12))

    # Executive Overview Table
    cur_val = sales_ml.get('current_sales', 0) if isinstance(sales_ml, dict) else 0
    prev_val = sales_ml.get('previous_sales', 0) if isinstance(sales_ml, dict) else 0
    pred_val = sales_ml.get('predicted_sales', 0) if isinstance(sales_ml, dict) else 0
    growth_val = sales_ml.get('growth_percentage', 0) if isinstance(sales_ml, dict) else 0

    exec_data = [
        [Paragraph("Current Month Sales", header_style), Paragraph("Previous Month Sales", header_style), Paragraph("Predicted Next Month", header_style), Paragraph("Projected Growth", header_style)],
        [
            Paragraph(format_currency(cur_val), bold_style),
            Paragraph(format_currency(prev_val), normal_style),
            Paragraph(format_currency(pred_val), bold_style),
            Paragraph(f"+{growth_val}%", bold_style)
        ]
    ]
    exec_table = Table(exec_data, colWidths=[135, 135, 135, 135])
    exec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(exec_table)
    story.append(Spacer(1, 16))

    # Monthly Breakdown Table
    story.append(Paragraph("<b>Month-by-Month Revenue Summary:</b>", bold_style))
    story.append(Spacer(1, 6))

    m_rows = [[Paragraph("Month & Year", header_style), Paragraph("Total Revenue (₹)", header_style), Paragraph("Transaction Count", header_style)]]
    for m in monthly_breakdown[:12]:
        m_rows.append([
            Paragraph(m['month'], normal_style),
            Paragraph(format_currency(m['total']), bold_style),
            Paragraph(str(m['count']), normal_style)
        ])

    m_table = Table(m_rows, colWidths=[180, 180, 180])
    m_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), accent_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(m_table)
    story.append(Spacer(1, 16))

    # Detailed Transactions Table
    story.append(Paragraph("<b>Detailed Sales Ledger:</b>", bold_style))
    story.append(Spacer(1, 6))

    ledger_rows = [[Paragraph("Date", header_style), Paragraph("Customer", header_style), Paragraph("Product", header_style), Paragraph("Region", header_style), Paragraph("Amount (₹)", header_style)]]
    for s in sales_list[:25]:
        date_str = s.sale_date.strftime('%b %d, %Y') if s.sale_date else 'N/A'
        cust_name = s.customer.name if s.customer else 'Client'
        prod_name = s.product.name if s.product else 'Product'
        ledger_rows.append([
            Paragraph(date_str, normal_style),
            Paragraph(cust_name[:20], normal_style),
            Paragraph(prod_name[:20], normal_style),
            Paragraph(s.region, normal_style),
            Paragraph(format_currency(s.total_amount), bold_style)
        ])

    ledger_table = Table(ledger_rows, colWidths=[90, 130, 130, 90, 100])
    ledger_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(ledger_table)
    story.append(Spacer(1, 20))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=10))
    footer_text = f"Report generated automatically by NexusAI Operating System on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    footer_style = ParagraphStyle('FooterStyle', parent=styles['Normal'], alignment=1, fontSize=8, textColor=colors.HexColor("#94a3b8"))
    story.append(Paragraph(footer_text, footer_style))

    doc.build(story)
    return output_path
