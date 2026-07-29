"""
mock_bc.py
==========
Mock Business Central data for demo and local development.

Uses realistic Sage Publishing data that mirrors real BC records.
Products have realistic prices for demo purposes.

Switch to live BC: set BC_MODE=live in .env
"""

CUSTOMERS = {
    "INTERNATIONAL BOOK DISTRIBUTORS": {
        "customer_id": "00018055",
        "currency": "INR",
        "country": "IN"
    },
    "CENTRAL NEWS AGENCY": {
        "customer_id": "00000082",
        "currency": "INR",
        "country": "IN"
    },
    "SURIYA BOOKSHOP, SOCIAL SCIENTISTS": {
        "customer_id": "00000274",
        "currency": "INR",
        "country": "LK"
    },
    "NATIONAL INSTITUTE OF PUBLIC COOPERATION": {
        "customer_id": "00000435",
        "currency": "INR",
        "country": "IN"
    }
}

PRODUCTS = {
    "An Introduction to Qualitative Research": {
        "item_no": "9789386062741",
        "unit_price": 850
    },
    "The Essential Guide to Doing Your Research Project": {
        "item_no": "9781446258965",
        "unit_price": 995
    },
    "Criminal Investigation": {
        "item_no": "9781412994279",
        "unit_price": 1200
    },
    "The Law of Journalism and Mass Communication": {
        "item_no": "9781506363226",
        "unit_price": 1100
    },
    "Concepts in International Relations: A New Introduction": {
        "item_no": "9781529669954",
        "unit_price": 1050
    },
    "Case Study Research and Applications": {
        "item_no": "9781506336169",
        "unit_price": 1150
    },
    "Research Design": {
        "item_no": "9780761910855",
        "unit_price": 1300
    },
    "Introduction to Criminology: Why Do They Do It": {
        "item_no": "9781506347561",
        "unit_price": 1100
    },
    "Introduction to Criminology: Theories, Methods, and Criminal Behavior": {
        "item_no": "9781412979719",
        "unit_price": 1050
    },
    "Criminology: The Essentials": {
        "item_no": "9781446256091",
        "unit_price": 950
    },
    "Professional Issues in Software Engineering": {
        "item_no": "9780748409518",
        "unit_price": 1450
    },
    "Coping with Life Stress": {
        "item_no": "0000000000000",
        "unit_price": 1500
    },
    "Performance Management": {
        "item_no": "2021015001201",
        "unit_price": 1800
    },
    "Technology-Based Health Promotion": {
        "item_no": "9781452230139",
        "unit_price": 2200
    }
}


def _normalise(text):
    """Normalises text for fuzzy matching."""
    text = text.strip().lower()
    text = " ".join(text.split())
    return text


def get_customer(organization):
    """
    Case-insensitive customer lookup.
    Returns customer dict or None if not found.
    """

    if not organization or not organization.strip():
        return None

    organization = organization.strip().lower()

    for name, customer in CUSTOMERS.items():
        if name.lower() == organization:
            return customer

    return None


def get_product(product_name, isbn=""):
    """
    Exact then normalised product lookup.
    isbn parameter accepted for interface compatibility
    with bc_items.py but not used in mock.
    """

    if not product_name:
        return None

    # Exact match first
    if product_name in PRODUCTS:
        return PRODUCTS[product_name]

    # Normalised match
    normalised_input = _normalise(product_name)

    for name, product in PRODUCTS.items():
        if _normalise(name) == normalised_input:
            return product

    return None


def validate_products(products):
    """
    Validates products against mock master data.
    Returns (validated_products, missing_products).
    """

    validated_products = []
    missing_products = []

    for product in products:

        product_record = get_product(
            product["name"],
            isbn=product.get("isbn", "")
        )

        if product_record:
            validated_products.append({
                "requested":   product,
                "master_data": product_record
            })
        else:
            missing_products.append(product["name"])

    return validated_products, missing_products