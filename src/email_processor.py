from document_reader import read_document
from classifier import classify_email
from decision_engine import evaluate
from audit_logger import log_decision
from human_intervention import intervene
from config import BC_MODE, JOURNALS_TEAM_EMAIL
from outlook_com import (
    save_attachments,
    mark_as_read,
    get_thread_context
)
from quote_generator import generate_quote
from quote_printer import print_quote
from pdf_generator import generate_pdf
from quote_review import review_quote
from outlook_draft import (
    create_outlook_draft,
    create_journal_forward_draft,
    create_availability_draft
)

if BC_MODE == "live":
    from bc_client import get_customer, validate_products
else:
    from mock_bc import get_customer, validate_products


# =============================================================
# Intent Sets
# =============================================================

INTENTS_SKIP_BC = {
    "Support Request",
    "Invoice Query",
    "Other",
}

JOURNAL_INTENTS = {
    "Journal Subscription",
    "Subscription Renewal",
}

JOURNAL_KEYWORDS = [
    "subscription", "subscribe", "journal", "periodical",
    "institutional access", "online access", "annual access",
    "institutional subscription", "renewal", "license",
    "e-access", "electronic access", "digital access",
    "volume", "issue", "multi-year", "perpetual access"
]


# =============================================================
# Journal Detection
# =============================================================

def _detect_journal_request(email_body, notes):
    """
    Scans email body and LLM notes for journal/subscription
    language regardless of primary intent classification.
    Allows mixed emails to process books AND flag journal part.
    """

    combined = (
        (email_body or "").lower() + " " + (notes or "").lower()
    )

    return any(kw in combined for kw in JOURNAL_KEYWORDS)


# =============================================================
# Quote History Check
# =============================================================

def _check_quote_history(conversation_id):
    """
    Checks audit_log.txt for prior approved quotes
    in this conversation thread.
    """

    if not conversation_id:
        return False

    try:
        with open("audit_log.txt", "r", encoding="utf-8") as f:
            log_content = f.read()

        return (
            conversation_id in log_content
            and "Quote Approved" in log_content
        )

    except FileNotFoundError:
        return False
    except Exception:
        return False


# =============================================================
# Main Processor
# =============================================================

def process_email(email, system_prompt, inbox=None):

    print("=" * 80)
    print("PROCESSING EMAIL")
    print("=" * 80)

    print(f"Subject : {email['subject']}")
    print(f"From    : {email['from']}")
    print(f"Received: {email['received']}")

    # -----------------------------------
    # Save Attachments
    # -----------------------------------

    saved_files = save_attachments(email["mail_item"])

    print("\nSaved Attachments")

    if saved_files:
        for file in saved_files:
            print(file)
    else:
        print("No attachments.")

    # -----------------------------------
    # Read Attachments
    # -----------------------------------

    attachment_text = ""

    for file in saved_files:
        print(f"\nReading: {file}")
        extracted = read_document(file)
        attachment_text += extracted + "\n\n"

    # -----------------------------------
    # Read Thread History
    # -----------------------------------

    thread_context  = ""
    prior_quote     = False

    if inbox is not None:

        thread_context = get_thread_context(
            email["mail_item"], inbox
        )

        if thread_context:
            conv_id    = email.get("conversation_id")
            prior_quote = _check_quote_history(conv_id)

            if prior_quote:
                print(
                    "\n  [Thread] Prior quote found for this "
                    "conversation — this may be a confirmation "
                    "or modification."
                )

    # -----------------------------------
    # Build LLM Prompt
    # -----------------------------------

    thread_section = (
        f"\n--------------------------------\n"
        f"\n{thread_context}\n"
        if thread_context
        else ""
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": (
                f"EMAIL SUBJECT\n\n{email['subject']}\n\n"
                f"--------------------------------\n\n"
                f"EMAIL BODY (LATEST — PRIMARY ACTION)\n\n"
                f"{email['body']}\n\n"
                f"--------------------------------\n\n"
                f"ATTACHMENT CONTENT\n\n{attachment_text}"
                f"{thread_section}"
            )
        }
    ]

    # -----------------------------------
    # LLM Classification
    # -----------------------------------

    result = classify_email(messages)

    print("\n========== EMAIL UNDERSTANDING ==========")
    print(f"Intent           : {result['intent']}")
    print(f"Confidence       : {result['confidence']}")
    print(f"Organization     : {result['organization']}")
    print(f"Contact Person   : {result['contact_person']}")

    print("\nProducts")
    if result["products"]:
        for product in result["products"]:
            edition = (
                f" [{product.get('edition', '')}]"
                if product.get("edition") else ""
            )
            isbn = (
                f" ISBN:{product.get('isbn','')}"
                if product.get("isbn") else ""
            )
            print(
                f"• {product['name']} "
                f"({product['quantity']})"
                f"{edition}{isbn}"
            )
    else:
        print("None")

    print("\nNotes")
    print(result["notes"])

    # -----------------------------------
    # Journal Detection (secondary scan)
    # -----------------------------------

    journal_detected = _detect_journal_request(
        email["body"], result["notes"]
    )

    if journal_detected and result["intent"] not in JOURNAL_INTENTS:
        print(
            "\n⚠  JOURNAL REQUEST DETECTED"
            "\n   This email may contain a journal subscription"
            " request alongside book orders."
            "\n   Books will be processed normally."
            "\n   Journal part will be forwarded separately."
        )

    # -----------------------------------
    # Early Routing — No BC Needed
    # -----------------------------------

    if result["intent"] in INTENTS_SKIP_BC:

        print(f"\n========== DECISION ==========")
        print(f"Action : ROUTE — {result['intent']}")
        print(f"Reason : {result['intent']} — no BC lookup required")

        if result["intent"] == "Support Request":
            print("\nRouting to Support Team...")
            log_decision(result, "Routed to Support", email=email)
        elif result["intent"] == "Invoice Query":
            print("\nRouting to Finance Team...")
            log_decision(result, "Routed to Finance", email=email)
        else:
            print("\nArchiving...")
            log_decision(result, "Archived", email=email)

        mark_as_read(email["mail_item"])
        print("Email marked as read.")
        print("\nProcessing Complete.\n")
        return

    if result["intent"] in JOURNAL_INTENTS:

        print(f"\n========== DECISION ==========")
        print(f"Action : ROUTE_JOURNALS")
        print(f"Reason : Journal subscription — routing to journals team")
        print("\nRouting to Journals Team...")
        log_decision(result, "Routed to Journals Team", email=email)

        if JOURNALS_TEAM_EMAIL:
            create_journal_forward_draft(
                email["mail_item"],
                JOURNALS_TEAM_EMAIL,
                "N/A"
            )
            print(f"Journal forward draft created. To: {JOURNALS_TEAM_EMAIL}")

        mark_as_read(email["mail_item"])
        print("Email marked as read.")
        print("\nProcessing Complete.\n")
        return

    # -----------------------------------
    # Business Central
    # -----------------------------------

    print("\n========== BUSINESS CENTRAL ==========")
    print(f"Mode: {'LIVE' if BC_MODE == 'live' else 'MOCK'}")

    customer = get_customer(result["organization"])

    if customer:
        print("\nCustomer Found")
        print(f"Customer ID : {customer['customer_id']}")
        print(f"Currency    : {customer['currency']}")
        print(f"Country     : {customer['country']}")
    else:
        print("\nCustomer NOT Found")

    validated_products, inactive_products, missing_products = (
        validate_products(result["products"])
    )

    print("\n========== PRODUCT VALIDATION ==========")

    if validated_products:
        print(f"\nActive items ({len(validated_products)}) — included in quote:")
        for item in validated_products:
            md = item["master_data"]
            price_currency = md.get("currency") or (
                customer["currency"] if customer else ""
            )
            orig = (
                f" ({md.get('orig_currency','')} "
                f"{md.get('orig_price',0):,.2f})"
                if md.get("orig_currency")
                and md.get("orig_currency") != "INR"
                else ""
            )
            edition_str = (
                f"\n  Edition     : {item['requested'].get('edition','')}"
                if item["requested"].get("edition") else ""
            )
            print(f"""
  Product     : {item['requested']['name']}{edition_str}
  Quantity    : {item['requested']['quantity']}
  Item Number : {md['item_no']}
  Unit Price  : INR {md['unit_price']:,.2f}{orig}""")

    if inactive_products:
        print(
            f"\n⚠  Inactive items ({len(inactive_products)}) "
            f"— NOT included (manual follow-up required):"
        )
        for item in inactive_products:
            md = item["master_data"]
            print(f"""
  Product     : {item['requested']['name']}
  Status      : {md.get('status_name', 'Inactive')}
  Last Price  : {md.get('currency','')} {md.get('unit_price',0):,.2f}
  Last Active : {md.get('last_active', 'Unknown')}
  Reason      : {(md.get('inactive_reason') or '')[:100]}""")

    if missing_products:
        print(f"\n✗  Not found in BC ({len(missing_products)}):")
        for product in missing_products:
            print(f"  • {product}")

    # -----------------------------------
    # Decision Engine
    # -----------------------------------

    all_unavailable = missing_products + [
        item["requested"]["name"] for item in inactive_products
    ]

    real_missing = [
        m for m in result["missing_information"]
        if m.lower() != "quantity"
    ]

    decision = evaluate(
        intent=result["intent"],
        confidence=result["confidence"],
        customer_found=(customer is not None),
        missing_products=all_unavailable,
        missing_information=real_missing,
        validated_products=validated_products
    )

    print("\n========== DECISION ==========")
    print(f"Action : {decision['action']}")
    print(f"Reason : {decision['reason']}")

    # -----------------------------------
    # Workflow Routing
    # -----------------------------------

    if decision["action"] in (
        "AUTO_PROCESS",
        "AUTO_PROCESS_PARTIAL",
        "AUTO_AVAILABILITY"
    ):

        # Availability Check — no quote needed
        if decision["action"] == "AUTO_AVAILABILITY":

            print("\n========== AVAILABILITY CONFIRMED ==========")

            for item in validated_products:
                md = item["master_data"]
                print(
                    f"\n  ✓ AVAILABLE: {item['requested']['name']}"
                    f"\n    ISBN      : {md['item_no']}"
                    f"\n    Price     : INR {md['unit_price']:,.2f}"
                    f"\n    Status    : {md.get('status_name', 'Active')}"
                )

            print("\nCreating availability confirmation draft...")
            create_availability_draft(
                validated_products,
                customer,
                email["mail_item"]
            )

            log_decision(result, "Availability Confirmed", email=email)
            mark_as_read(email["mail_item"])
            print("Email marked as read.")
            print("\nProcessing Complete.\n")
            return

        # Quote workflow
        print("\nGenerating Quote...")

        quote = generate_quote(
            result,
            customer,
            validated_products,
            email
        )

        print_quote(quote)

        # Initial PDF
        pdf_path = generate_pdf(quote)
        print(f"\nPDF Generated: {pdf_path}")

        # Human review
        partial_missing = decision.get("missing_products", [])

        approved = review_quote(
            quote,
            pdf_path,
            inactive_products=inactive_products,
            missing_products=missing_products
        )

        if approved:

            print("\nQuote approved.")

            # Regenerate PDF with any price updates from review
            pdf_path = generate_pdf(quote)
            print(f"Final PDF: {pdf_path}")

            log_decision(result, "Quote Approved", email=email)
            mark_as_read(email["mail_item"])
            print("Email marked as read.")

            print("\nCreating Outlook Draft...")
            create_outlook_draft(quote, pdf_path, email["mail_item"])
            print("Outlook draft created.")

            # Forward journal part if detected
            if journal_detected and result["intent"] not in JOURNAL_INTENTS:
                if JOURNALS_TEAM_EMAIL:
                    print("\nForwarding journal request to journals team...")
                    create_journal_forward_draft(
                        email["mail_item"],
                        JOURNALS_TEAM_EMAIL,
                        quote["quote_number"]
                    )
                    print(f"Journal forward draft created. To: {JOURNALS_TEAM_EMAIL}")
                    log_decision(
                        result,
                        "Journal Request Forwarded",
                        email=email
                    )
                else:
                    print(
                        "\n⚠  Journal request detected but "
                        "JOURNALS_TEAM_EMAIL not set in .env"
                    )

        else:
            print("\nQuote rejected.")
            log_decision(result, "Quote Rejected", email=email)
            print("Workflow stopped for manual changes.")

    elif decision["action"] == "HUMAN_INTERVENTION":

        intervene(decision["reason"])
        log_decision(
            result,
            f"Human Intervention — {decision['reason']}",
            email=email
        )

    else:
        # Fallback for any other routing
        log_decision(result, decision["action"], email=email)

    print("\nProcessing Complete.\n")