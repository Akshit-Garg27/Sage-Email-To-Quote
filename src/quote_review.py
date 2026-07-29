"""
quote_review.py
===============
Human review step for generated quotes.

Handles:
  - Inactive / blocked / out of print items
    shown clearly to reviewer and noted for customer
  - Missing products (not in BC at all)
  - Standard approve/reject flow
"""

from bc_title_master import STATUS_ACTIVE


def _show_item_issues(quote, inactive_products, missing_products):
    """
    Shows all item status issues to the reviewer before approval.
    These items are NOT in the quote — they need manual follow-up.
    """

    if not inactive_products and not missing_products:
        return

    print("\n" + "=" * 90)
    print("ITEMS EXCLUDED FROM QUOTE — MANUAL FOLLOW-UP REQUIRED")
    print("=" * 90)

    if inactive_products:
        print(
            f"\n⚠  {len(inactive_products)} item(s) found in BC "
            f"but NOT included in quote:"
        )

        for item in inactive_products:
            md = item["master_data"]
            print(f"\n  Title       : {item['requested']['name']}")
            print(f"  ISBN        : {md.get('item_no', '')}")
            print(f"  Status      : {md.get('status_name', 'Inactive')}")
            if md.get("inactive_reason"):
                print(f"  BC Reason   : {md['inactive_reason'][:100]}")
            if md.get("last_active"):
                print(f"  Last Active : {md['last_active']}")
            print(
                f"  Last Price  : {md.get('currency','')} "
                f"{md.get('unit_price',0):,.2f}"
            )
            print(
                "  Action      : Contact customer with status "
                "and offer alternative edition if available."
            )

    if missing_products:
        print(
            f"\n✗  {len(missing_products)} item(s) not found in BC:"
        )
        for product in missing_products:
            print(f"  • {product}")
        print("  These may be from another publisher.")


def _build_customer_note(quote, inactive_products, missing_products):
    """
    Builds the note section for the customer about
    item status issues — included in the Outlook draft.
    """

    inactive_in_quote = [
        item for item in quote.get("items", [])
        if item.get("item_status", STATUS_ACTIVE) != STATUS_ACTIVE
    ]

    if not inactive_in_quote and not missing_products:
        return ""

    lines = []

    if inactive_in_quote:
        lines.append("Please note the following regarding some titles:")
        lines.append("")
        for item in inactive_in_quote:
            status = item.get("status_name", "Inactive")
            title  = item.get("description", "")
            isbn   = item.get("item_no", "")

            if "Out of Print" in status:
                lines.append(
                    f"• {title} (ISBN: {isbn}) — This title is currently "
                    f"Out of Print. The price shown is the last known price. "
                    f"Please contact us to discuss alternative editions."
                )
            elif "Superseded" in status or "Blocked" in status:
                lines.append(
                    f"• {title} (ISBN: {isbn}) — A newer edition of this "
                    f"title may be available. The price shown is for the "
                    f"edition referenced. Please confirm the required edition."
                )
            else:
                lines.append(
                    f"• {title} (ISBN: {isbn}) — Status: {status}. "
                    f"Please contact us to confirm availability."
                )
        lines.append("")

    if missing_products:
        lines.append(
            "The following title(s) could not be included "
            "in this quotation:"
        )
        for product in missing_products:
            lines.append(f"• {product}")
        lines.append(
            "These titles may be available through other publishers "
            "or may require separate pricing. Please contact us for details."
        )

    return "\n".join(lines)


def review_quote(quote, pdf_path, inactive_products=None, missing_products=None):
    """
    Human review step for a generated quote.

    Shows:
      - Item status issues (inactive, blocked, out of print)
      - Items not found in BC
      - Full quote summary
      - Approve / Reject

    Returns:
      True  — approved
      False — rejected
      Also returns customer_note for use in Outlook draft
    """

    missing_products = missing_products or []

    # Show item issues
    _show_item_issues(quote, inactive_products or [], missing_products or [])

    # Build customer note
    customer_note = _build_customer_note(quote, inactive_products or [], missing_products or [])

    # Store in quote for outlook_draft to use
    quote["customer_note"] = customer_note

    print("\n")
    print("=" * 90)
    print("QUOTE REVIEW")
    print("=" * 90)

    print(f"Quote Number  : {quote['quote_number']}")
    print(f"Customer      : {quote['customer']['organization']}")
    print(f"Currency      : {quote['customer']['currency']}")
    print(f"Items in Quote: {len(quote['items'])}")

    # Count by status
    active_count   = sum(
        1 for i in quote["items"]
        if i.get("item_status", STATUS_ACTIVE) == STATUS_ACTIVE
    )
    inactive_count = len(quote["items"]) - active_count

    if inactive_count > 0:
        print(
            f"  Active      : {active_count} items"
        )
        print(
            f"  ⚠ Inactive  : {inactive_count} items "
            f"(see status review above)"
        )

    if missing_products:
        print(f"Items Excluded: {len(missing_products)} (not in BC)")

    print(
        f"Grand Total   : "
        f"{quote['customer']['currency']} "
        f"{quote['pricing']['grand_total']:,.2f}"
    )
    print(f"PDF           : {pdf_path}")

    if customer_note:
        print(
            "\n  Customer note will be included in the Outlook draft."
        )

    print("\nPlease review the generated PDF before approving.")
    print("\nReview Options")
    print("-" * 90)
    print("1. Approve Quote")
    print("2. Reject Quote")
    print("-" * 90)

    while True:

        choice = input("\nEnter your choice (1 or 2): ").strip()

        if choice == "1":
            print("\nQuote Approved.\n")
            return True

        elif choice == "2":
            print("\nQuote Rejected.\n")
            return False

        else:
            print("Invalid choice. Please enter 1 or 2.")