import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable
)


# ---------------------------------
# Sage Brand Colours
# ---------------------------------

SAGE_GREEN  = colors.HexColor("#00A499")
SAGE_DARK   = colors.HexColor("#1A1A2E")
SAGE_LIGHT  = colors.HexColor("#F5F5F5")
SAGE_ACCENT = colors.HexColor("#004B55")
WHITE       = colors.white
LIGHT_GREY  = colors.HexColor("#E8E8E8")
MID_GREY    = colors.HexColor("#666666")


def _get_currency_symbol(currency_code):
    """Maps currency code to symbol."""
    symbols = {
        "INR": "INR",
        "USD": "USD",
        "GBP": "GBP",
        "EUR": "EUR",
        "AUD": "AUD",
    }
    return symbols.get(currency_code, currency_code)


def generate_pdf(quote):

    # ---------------------------------
    # Setup
    # ---------------------------------

    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    quotes_folder = os.path.join(project_root, "quotes")
    os.makedirs(quotes_folder, exist_ok=True)

    pdf_path = os.path.join(
        quotes_folder,
        f"{quote['quote_number']}.pdf"
    )

    customer = quote["customer"]
    pricing  = quote["pricing"]
    currency = _get_currency_symbol(customer["currency"])

    document = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---------------------------------
    # Custom Styles
    # ---------------------------------

    style_company = ParagraphStyle(
        "CompanyName",
        fontSize=22,
        textColor=SAGE_ACCENT,
        fontName="Helvetica-Bold",
        spaceAfter=2
    )

    style_tagline = ParagraphStyle(
        "Tagline",
        fontSize=9,
        textColor=MID_GREY,
        fontName="Helvetica",
        spaceAfter=4
    )

    style_doc_title = ParagraphStyle(
        "DocTitle",
        fontSize=14,
        textColor=SAGE_GREEN,
        fontName="Helvetica-Bold",
        spaceAfter=4
    )

    style_section = ParagraphStyle(
        "SectionHeader",
        fontSize=9,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        spaceAfter=0
    )

    style_label = ParagraphStyle(
        "Label",
        fontSize=9,
        textColor=MID_GREY,
        fontName="Helvetica",
        leading=14
    )

    style_value = ParagraphStyle(
        "Value",
        fontSize=9,
        textColor=SAGE_DARK,
        fontName="Helvetica-Bold",
        leading=14
    )

    style_footer = ParagraphStyle(
        "Footer",
        fontSize=8,
        textColor=MID_GREY,
        fontName="Helvetica",
        alignment=TA_CENTER,
        leading=12
    )

    style_total_label = ParagraphStyle(
        "TotalLabel",
        fontSize=11,
        textColor=WHITE,
        fontName="Helvetica-Bold"
    )

    style_total_value = ParagraphStyle(
        "TotalValue",
        fontSize=11,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_RIGHT
    )

    # ---------------------------------
    # Header — Company + Document Info
    # ---------------------------------

    header_data = [[
        # Left — Company name and tagline
        [
            Paragraph("SAGE PUBLISHING", style_company),
            Paragraph(
                "Scholarly Publishing · Books · Journals",
                style_tagline
            ),
        ],
        # Right — Document title and quote details
        [
            Paragraph("SALES QUOTATION", style_doc_title),
            Paragraph(
                f"Quote No: <b>{quote['quote_number']}</b>",
                style_label
            ),
            Paragraph(
                f"Date: <b>{quote['date']}</b>",
                style_label
            ),
            Paragraph(
                f"Valid Until: <b>{quote['expiry_date']}</b>",
                style_label
            ),
            Paragraph(
                f"Status: <b>{quote['status']}</b>",
                style_label
            ),
        ]
    ]]

    header_table = Table(
        header_data,
        colWidths=["55%", "45%"]
    )

    header_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("ALIGN",        (1, 0), (1, 0),   "RIGHT"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]))

    elements.append(header_table)

    # Green divider line
    elements.append(
        HRFlowable(
            width="100%",
            thickness=3,
            color=SAGE_GREEN,
            spaceAfter=12
        )
    )

    # ---------------------------------
    # Customer + Source Info (side by side)
    # ---------------------------------

    def section_header(title):
        """Creates a coloured section header bar."""
        t = Table(
            [[Paragraph(title, style_section)]],
            colWidths=["100%"]
        )
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), SAGE_ACCENT),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ]))
        return t

    def info_row(label, value):
        return [
            Paragraph(label, style_label),
            Paragraph(str(value), style_value)
        ]

    # Customer section
    elements.append(section_header("BILL TO"))
    elements.append(Spacer(1, 4))

    customer_data = [
        info_row("Organisation", customer["organization"]),
        info_row("Contact",      customer["contact_person"]),
        info_row("Email",        customer["email"]),
        info_row("Country",      customer["country"]),
        info_row("Currency",     customer["currency"]),
    ]

    customer_table = Table(
        customer_data,
        colWidths=["25%", "75%"]
    )

    customer_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS",(0, 0),(-1, -1), [WHITE, SAGE_LIGHT]),
    ]))

    elements.append(customer_table)
    elements.append(Spacer(1, 14))

    # ---------------------------------
    # Items Table
    # ---------------------------------

    elements.append(section_header("ITEMS"))
    elements.append(Spacer(1, 4))

    table_data = [[
        Paragraph("<b>ISBN / Item No</b>", style_label),
        Paragraph("<b>Description</b>",    style_label),
        Paragraph("<b>Qty</b>",            style_label),
        Paragraph(f"<b>Unit Price ({currency})</b>", style_label),
        Paragraph(f"<b>Total ({currency})</b>",      style_label),
    ]]

    for item in quote["items"]:
        table_data.append([
            Paragraph(str(item["item_no"]),      style_label),
            Paragraph(item["description"],        style_label),
            Paragraph(str(item["quantity"]),      style_label),
            Paragraph(f"{item['unit_price']:,.2f}", style_label),
            Paragraph(f"{item['line_total']:,.2f}", style_label),
        ])

    items_table = Table(
        table_data,
        colWidths=["18%", "42%", "8%", "16%", "16%"]
    )

    # Build alternating row colours
    row_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0),  SAGE_LIGHT),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, LIGHT_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (2, 1), (-1, -1), "RIGHT"),
        ("ALIGN",         (2, 0), (4, 0),   "RIGHT"),
        ("LINEBELOW",     (0, 0), (-1, 0),  1, SAGE_GREEN),
    ]

    for i in range(1, len(table_data)):
        if i % 2 == 0:
            row_styles.append(
                ("BACKGROUND", (0, i), (-1, i), SAGE_LIGHT)
            )

    items_table.setStyle(TableStyle(row_styles))

    elements.append(items_table)
    elements.append(Spacer(1, 8))

    # ---------------------------------
    # Totals
    # ---------------------------------

    totals_data = [
        [
            Paragraph("Subtotal", style_label),
            Paragraph(
                f"{currency} {pricing['subtotal']:,.2f}",
                ParagraphStyle(
                    "Right",
                    fontSize=9,
                    alignment=TA_RIGHT,
                    fontName="Helvetica"
                )
            )
        ],
        [
            Paragraph("Discount", style_label),
            Paragraph(
                f"{currency} {pricing['discount']:,.2f}",
                ParagraphStyle(
                    "Right",
                    fontSize=9,
                    alignment=TA_RIGHT,
                    fontName="Helvetica"
                )
            )
        ],
        [
            Paragraph("Tax", style_label),
            Paragraph(
                f"{currency} {pricing['tax']:,.2f}",
                ParagraphStyle(
                    "Right",
                    fontSize=9,
                    alignment=TA_RIGHT,
                    fontName="Helvetica"
                )
            )
        ],
    ]

    totals_table = Table(
        totals_data,
        colWidths=["80%", "20%"]
    )

    totals_table.setStyle(TableStyle([
        ("ALIGN",        (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LINEBELOW",    (0, -1), (-1, -1), 0.5, LIGHT_GREY),
    ]))

    elements.append(totals_table)
    elements.append(Spacer(1, 4))

    # Grand Total bar
    grand_total_data = [[
        Paragraph("GRAND TOTAL", style_total_label),
        Paragraph(
            f"{currency} {pricing['grand_total']:,.2f}",
            style_total_value
        )
    ]]

    grand_total_table = Table(
        grand_total_data,
        colWidths=["65%", "35%"]
    )

    grand_total_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), SAGE_ACCENT),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(grand_total_table)
    elements.append(Spacer(1, 20))

    # ---------------------------------
    # Footer
    # ---------------------------------

    elements.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=SAGE_GREEN,
            spaceAfter=8
        )
    )

    footer_lines = [
        "Thank you for choosing Sage Publishing.",
        "This quotation is valid for 30 days from the date of issue.",
        "For queries please contact your Sage Publishing representative.",
        "www.sagepub.in",
    ]

    for line in footer_lines:
        elements.append(Paragraph(line, style_footer))

    document.build(elements)

    return pdf_path