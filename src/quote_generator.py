from datetime import datetime, timedelta


def generate_quote(
    result,
    customer,
    validated_products,
    email
):

    today = datetime.now()

    subtotal = 0

    quote = {

        "quote_number": f"Q-{today.strftime('%Y%m%d%H%M%S')}",

        "date": today.strftime("%d-%b-%Y"),

        "expiry_date": (
            today + timedelta(days=30)
        ).strftime("%d-%b-%Y"),

        "status": "Draft",

        "customer": {

            "customer_id": customer["customer_id"],

            "organization": result["organization"],

            "contact_person": result["contact_person"],

            "email": email["from"],

            "country": customer["country"],

            "currency": customer["currency"]
        },

        "sales_information": {

            "source": "Outlook",

            "email_subject": email["subject"],

            "received": email["received"]
        },

        "items": [],

        "pricing": {

            "subtotal": 0,

            "discount": 0,

            "tax": 0,

            "grand_total": 0
        }

    }

    for item in validated_products:

        # Default quantity to 1 if not specified
        quantity = item["requested"]["quantity"]
        if not quantity or quantity == 0:
            quantity = 1

        unit_price = item["master_data"]["unit_price"]

        line_total = quantity * unit_price

        subtotal += line_total

        quote["items"].append(

            {

                "item_no": item["master_data"]["item_no"],

                "description": item["requested"]["name"],

                "quantity": quantity,

                "unit_price": unit_price,

                "line_total": line_total

            }

        )

    quote["pricing"]["subtotal"] = subtotal

    quote["pricing"]["grand_total"] = subtotal

    return quote