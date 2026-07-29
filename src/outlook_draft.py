"""
outlook_draft.py
================
Creates Outlook reply drafts for different scenarios:

1. create_outlook_draft()
   Standard quote reply — uses LLM-composed email body
   instead of hardcoded template

2. create_journal_forward_draft()
   Forwards email to journals team with cover note

3. create_availability_draft()
   Confirms book availability to customer
"""

import win32com.client
from email_composer import compose_email


def create_outlook_draft(quote, pdf_path, mail_item):
    """
    Creates a reply draft with:
    - LLM-composed professional email body
    - PDF quotation attached
    - Original email quoted below

    Falls back to a clean template if LLM composition fails.
    """

    reply = mail_item.Reply()

    # Build email dict for composer
    original_email = {
        "subject": mail_item.Subject,
        "body":    mail_item.Body or ""
    }

    # Try LLM-composed body first
    try:
        body = compose_email(quote, original_email)
        print("  [Draft] LLM email composed successfully.")

    except Exception as e:
        print(f"  [Draft] LLM composition failed: {e} — using template.")
        body = _fallback_body(quote)

    # Add PDF attachment note if not already mentioned
    body = body.strip()
    if "attach" not in body.lower():
        body += (
            f"\n\nPlease find our quotation "
            f"{quote['quote_number']} attached."
        )

    reply.Body = body + "\n\n" + reply.Body
    reply.Attachments.Add(pdf_path)
    reply.Save()

    return True


def create_journal_forward_draft(mail_item, journals_team_email, quote_number):
    """
    Forwards original email to journals team with cover note.
    Created when journal language is detected in a book quote email.
    """

    forward = mail_item.Forward()
    forward.To = journals_team_email

    cover = (
        f"Hi,\n\n"
        f"This email contains a journal subscription request "
        f"alongside a book order.\n\n"
        f"The book order has been processed — "
        f"quotation {quote_number} sent to the customer.\n\n"
        f"Please handle the journal subscription part.\n\n"
        f"Original email forwarded below.\n\n"
        f"Thanks,\n"
        f"Email-to-Quote Automation\n"
        f"Sage Publishing\n"
        f"---\n"
    )

    forward.Body       = cover + "\n\n" + forward.Body
    forward.Subject    = f"[JOURNALS] Subscription Request — Ref: {quote_number}"
    forward.Save()

    return True


def create_availability_draft(validated_products, customer, mail_item):
    """
    Creates a reply confirming book availability.
    Used for Availability Check intent — no PDF needed.
    """

    reply = mail_item.Reply()

    contact = customer.get("contact_person", "") or "Sir/Madam"

    lines = [
        f"Dear {contact},",
        "",
        "Thank you for your enquiry. We are pleased to confirm "
        "the availability of the following title(s):",
        "",
    ]

    for item in validated_products:
        md    = item["master_data"]
        title = item["requested"]["name"]
        isbn  = md.get("item_no", "")
        price = md.get("unit_price", 0)

        lines.append(f"Title  : {title}")
        if isbn:
            lines.append(f"ISBN   : {isbn}")
        lines.append(f"Price  : INR {price:,.2f}")
        lines.append(f"Status : Available")
        lines.append("")

    lines += [
        "Should you require a formal quotation or wish to "
        "place an order, please do not hesitate to contact us.",
        "",
        "Kind Regards,",
        "Sales Team",
        "Sage Publishing",
    ]

    reply.Body = "\n".join(lines) + "\n\n" + reply.Body
    reply.Save()

    return True


def _fallback_body(quote):
    """
    Simple template used if LLM composition fails.
    Always available, no external dependency.
    """

    customer = quote["customer"]
    contact  = customer.get("contact_person", "") or "Sir/Madam"

    return (
        f"Dear {contact},\n\n"
        f"Thank you for your enquiry.\n\n"
        f"Please find attached our quotation "
        f"{quote['quote_number']} for your requested titles.\n\n"
        f"Quote Number : {quote['quote_number']}\n"
        f"Valid Until  : {quote['expiry_date']}\n"
        f"Currency     : {customer['currency']}\n"
        f"Grand Total  : {customer['currency']} "
        f"{quote['pricing']['grand_total']:,.2f}\n\n"
        f"Please do not hesitate to contact us if you have "
        f"any questions.\n\n"
        f"Kind Regards,\n"
        f"Sales Team\n"
        f"Sage Publishing"
    )