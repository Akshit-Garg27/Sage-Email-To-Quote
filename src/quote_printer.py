def print_quote(quote):

    currency = quote["customer"]["currency"]

    print("\n")
    print("=" * 90)
    print(" " * 30 + "SALES QUOTATION (DRAFT)")
    print("=" * 90)

    # ----------------------------------------------------
    # Quote Information
    # ----------------------------------------------------

    print("\nQUOTE INFORMATION")

    print(f"Quote Number : {quote['quote_number']}")
    print(f"Date         : {quote['date']}")
    print(f"Valid Until  : {quote['expiry_date']}")
    print(f"Status       : {quote['status']}")

    # ----------------------------------------------------
    # Customer Information
    # ----------------------------------------------------

    customer = quote["customer"]

    print("\n" + "-" * 90)
    print("CUSTOMER INFORMATION")
    print("-" * 90)

    print(f"Customer ID     : {customer['customer_id']}")
    print(f"Organization    : {customer['organization']}")
    print(f"Contact Person  : {customer['contact_person']}")
    print(f"Email           : {customer['email']}")
    print(f"Country         : {customer['country']}")
    print(f"Currency        : {customer['currency']}")

    # ----------------------------------------------------
    # Source Information
    # ----------------------------------------------------

    source = quote["sales_information"]

    print("\n" + "-" * 90)
    print("SOURCE INFORMATION")
    print("-" * 90)

    print(f"Source          : {source['source']}")
    print(f"Email Subject   : {source['email_subject']}")
    print(f"Received        : {source['received']}")

    # ----------------------------------------------------
    # Items
    # ----------------------------------------------------

    print("\n" + "-" * 90)
    print("ITEMS")
    print("-" * 90)

    print(
        f"{'Item No':<15}"
        f"{'Description':<38}"
        f"{'Qty':>6}"
        f"{'Unit Price':>16}"
        f"{'Line Total':>15}"
    )

    print("-" * 90)

    for item in quote["items"]:

        print(
            f"{item['item_no']:<15}"
            f"{item['description'][:37]:<38}"
            f"{item['quantity']:>6}"
            f"{currency} {item['unit_price']:>12,.2f}"
            f"{currency} {item['line_total']:>11,.2f}"
        )

    # ----------------------------------------------------
    # Pricing
    # ----------------------------------------------------

    pricing = quote["pricing"]

    print("-" * 90)

    print(f"\nSubtotal     : {currency} {pricing['subtotal']:>12,.2f}")
    print(f"Discount     : {currency} {pricing['discount']:>12,.2f}")
    print(f"Tax          : {currency} {pricing['tax']:>12,.2f}")

    print("=" * 90)
    print(f"GRAND TOTAL  : {currency} {pricing['grand_total']:>12,.2f}")
    print("=" * 90)

    print("\nEnd of Draft Quotation\n")