"""
bc_items.py
===========
Product/Item lookup against Business Central Items API.

Pricing from BooksItem_BI (Books Title Master) via bc_title_master.py.
Exchange rate conversion to INR via bc_exchange_rates.py.

Public interface:
  get_product(name, isbn="") -> dict | None
  validate_products(products) -> (validated, inactive, missing)

THREE lists returned:
  validated : active items with INR prices -> quote
  inactive  : blocked/out-of-print -> manual follow-up
  missing   : not in BC -> excluded
"""

import requests
from bc_auth import get_bc_token
from bc_company import get_company_id
from bc_errors import BCAPIError, BCNetworkError, retry_with_backoff
import bc_cache
from bc_title_master import get_title_price, STATUS_ACTIVE
from bc_exchange_rates import convert as fx_convert
from config import BC_TENANT_ID, BC_ENVIRONMENT


def _items_url(company_id):
    return (
        f"https://api.businesscentral.dynamics.com/v2.0/"
        f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/api/v2.0/"
        f"companies({company_id})/items"
    )


def get_product(product_name, isbn=""):
    """
    Looks up a product by name or ISBN.
    Returns pricing from Books Title Master converted to INR.
    """

    if not product_name or not product_name.strip():
        return None

    name_key = product_name.strip().lower()

    # Cache check by name
    cached = bc_cache.get_product(name_key)
    if not isinstance(cached, bc_cache._CacheMiss):
        if cached:
            print(f"  [BC Items] Cache hit: '{product_name}'")
        return cached

    # Cache check by isbn
    if isbn:
        clean_isbn = isbn.replace("-", "").replace(" ", "").strip("/")
        if clean_isbn:
            isbn_cached = bc_cache.get_product(clean_isbn.lower())
            if not isinstance(isbn_cached, bc_cache._CacheMiss):
                if isbn_cached:
                    print(f"  [BC Items] Cache hit by ISBN")
                return isbn_cached

    print(f"  [BC Items] Looking up: '{product_name}'")

    try:
        result = retry_with_backoff(
            lambda: _fetch_item(product_name, name_key, isbn)
        )
        bc_cache.set_product(name_key, result)
        if isbn:
            clean = isbn.replace("-", "").replace(" ", "").strip("/")
            if clean:
                bc_cache.set_product(clean.lower(), result)
        return result

    except Exception as e:
        print(f"  [BC Items] ERROR: {type(e).__name__}: {e}")
        return None


def validate_products(products):
    """
    Validates products. Returns THREE lists:
      validated_products : active with INR prices -> quote
      inactive_products  : blocked/OOP -> follow-up
      missing_products   : not in BC -> excluded
    """

    validated_products = []
    inactive_products  = []
    missing_products   = []

    for product in products:

        product_record = get_product(
            product["name"],
            isbn=product.get("isbn", "")
        )

        if product_record:
            status = product_record.get("item_status", STATUS_ACTIVE)
            if status == STATUS_ACTIVE:
                validated_products.append({
                    "requested":   product,
                    "master_data": product_record
                })
            else:
                inactive_products.append({
                    "requested":   product,
                    "master_data": product_record
                })
        else:
            missing_products.append(product["name"])

    return validated_products, inactive_products, missing_products


def _fetch_item(product_name, name_key, isbn=""):
    """
    Fetches item from BC using multi-strategy lookup.

    Lookup order:
    1. Direct ISBN search in BooksItem_BI (most reliable)
    2. BooksItem_BI Sage_Title exact match
    3. BooksItem_BI Sage_Title + edition matching
    4. Standard items API displayName exact match
    5. BooksItem_BI subtitle word search
    """

    token      = get_bc_token()
    company_id = get_company_id()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # 1. Direct ISBN search (fastest, most reliable)
    if isbn:
        clean = isbn.replace("-", "").replace(" ", "").strip("/")
        if clean.isdigit() and len(clean) >= 10:
            print(f"  [BC Items] Trying ISBN: {clean}")
            item = _search_by_number(headers, company_id, clean)
            if item:
                return _map_item(item)

    # Also try ISBN embedded in product_name string
    embedded = _search_by_number(headers, company_id, product_name)
    if embedded:
        return _map_item(embedded)

    # 2. Standard items API exact match (fast)
    item = _search_by_name(headers, company_id, name_key)
    if item:
        return _map_item(item)

    # 3. BooksItem_BI search — handles split titles
    # This is the key search for titles without ISBNs
    bi_result = _fetch_from_books_bi_by_title(product_name)
    if bi_result:
        return bi_result

    print(f"  [BC Items] Not found: '{product_name}'")
    return None


def _search_by_name(headers, company_id, name_key):
    try:
        response = requests.get(
            _items_url(company_id),
            headers=headers,
            params={
                "$filter": f"tolower(displayName) eq '{name_key}'",
                "$select": "id,number,displayName,unitPrice,type",
                "$top": 1
            },
            timeout=30
        )
        if response.ok:
            items = response.json().get("value", [])
            return items[0] if items else None
        if not response.ok:
            raise BCAPIError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )
    except (BCAPIError, BCNetworkError):
        raise
    except requests.exceptions.Timeout:
        raise BCNetworkError("Item lookup timed out.")
    except requests.exceptions.ConnectionError:
        raise BCNetworkError("Cannot connect to BC API.")
    return None


def _search_by_number(headers, company_id, product_name):
    cleaned = product_name.replace("-", "").replace(" ", "").strip("/")
    if not cleaned.isdigit() or len(cleaned) < 10:
        return None
    try:
        response = requests.get(
            _items_url(company_id),
            headers=headers,
            params={
                "$filter": f"number eq '{cleaned}'",
                "$select": "id,number,displayName,unitPrice,type",
                "$top": 1
            },
            timeout=30
        )
        if response.ok:
            items = response.json().get("value", [])
            if items:
                print(f"  [BC Items] Found by ISBN: '{cleaned}'")
                return items[0]
    except Exception:
        pass
    return None


def _search_by_partial_title(headers, company_id, product_name):
    """
    Partial title search using contains() on significant words.
    Used as last resort when exact match and ISBN both fail.
    Requires at least 2 significant words to match to avoid
    false positives.
    """

    words = [
        w for w in product_name.split()
        if len(w) > 4
        and w.lower() not in {
            "about", "their", "these", "there",
            "which", "would", "could", "should",
            "other", "being", "after", "under"
        }
    ]

    if len(words) < 2:
        return None

    # Use first two significant words for contains search
    search_term = words[0]

    print(
        f"  [BC Items] Trying partial search: "
        f"contains '{search_term}'..."
    )

    try:
        response = requests.get(
            _items_url(get_company_id()),
            headers=headers,
            params={
                "$filter": f"contains(tolower(displayName), "
                           f"'{search_term.lower()}')",
                "$select": "id,number,displayName,unitPrice,type",
                "$top":    10
            },
            timeout=30
        )

        if not response.ok:
            return None

        items = response.json().get("value", [])

        if not items:
            return None

        # Validate match — require 2 significant words overlap
        input_words = set(
            w.lower() for w in product_name.split()
            if len(w) > 4
        )

        for item in items:
            bc_title = (item.get("displayName") or "").lower()
            bc_words = set(
                w for w in bc_title.split() if len(w) > 4
            )
            overlap = input_words & bc_words

            if len(overlap) >= 2:
                print(
                    f"  [BC Items] Partial match: "
                    f"{item.get('displayName', '')[:45]} "
                    f"(overlap: {overlap})"
                )
                return item

    except Exception as e:
        print(f"  [BC Items] Partial search error: {e}")

    return None


def _fetch_from_books_bi_by_title(product_name):
    """
    Searches BooksItem_BI directly by title as last resort.

    This bypasses the items API entirely and goes straight
    to the Books Title Master which has:
    - Full Sage_Title + Sage_Sub_Title
    - Real Sale_Price
    - Active/Blocked status

    Used when the items API displayName does not match
    because it only stores the short title without subtitle.
    """

    from bc_title_master import get_title_price, STATUS_ACTIVE
    from bc_exchange_rates import convert as fx_convert

    price_info = get_title_price("", product_name)

    if not price_info:
        print(f"  [BC Items] Not found in BooksItem_BI: '{product_name}'")
        return None

    orig_price    = float(price_info["price"])
    orig_currency = price_info["currency"]

    if orig_currency and orig_currency != "INR":
        inr_price = fx_convert(orig_price, orig_currency, "INR")
        print(
            f"  [BC Items] BooksItem_BI FX: "
            f"{orig_currency} {orig_price} → INR {inr_price:,.2f}"
        )
    else:
        inr_price = orig_price

    result = {
        "item_no":         price_info.get("isbn", ""),
        "unit_price":      inr_price,
        "orig_price":      orig_price,
        "orig_currency":   orig_currency,
        "currency":        "INR",
        "item_status":     price_info["status"],
        "status_name":     price_info["status_name"],
        "inactive_reason": price_info.get("reason"),
        "sage_title":      price_info.get("sage_title", product_name),
        "last_active":     price_info.get("last_active", ""),
        "edition":         price_info.get("edition", ""),
    }

    print(
        f"  [BC Items] Found via BooksItem_BI: "
        f"{price_info.get('sage_title', product_name)[:40]} "
        f"(Price: INR {inr_price:,.2f}, "
        f"Status: {price_info['status']})"
    )

    return result


def _map_item(item):
    """
    Maps BC item to result dict.
    Gets real price from Books Title Master.
    Converts to INR using BC exchange rates.
    """

    isbn  = item.get("number", "")
    title = item.get("displayName", "")

    # Get price info from Books Title Master
    price_info = get_title_price(isbn, title)

    if price_info:
        orig_price   = float(price_info["price"])
        orig_currency = price_info["currency"]

        # Convert to INR explicitly here as safety net
        # (bc_title_master also sets inr_price but we
        # recalculate to ensure it is always correct)
        if orig_currency and orig_currency != "INR":
            inr_price = fx_convert(orig_price, orig_currency, "INR")
            print(
                f"  [BC Items] FX: {orig_currency} {orig_price} "
                f"→ INR {inr_price:,.2f}"
            )
        elif orig_currency == "INR":
            inr_price = orig_price
        else:
            # No currency info — use as-is
            inr_price = price_info.get("inr_price", orig_price)

        item_status     = price_info["status"]
        status_name     = price_info["status_name"]
        inactive_reason = price_info.get("reason")
        sage_title      = price_info.get("sage_title", title)
        last_active     = price_info.get("last_active", "")
        edition         = price_info.get("edition", "")

    else:
        orig_price      = 0.0
        orig_currency   = ""
        inr_price       = 0.0
        item_status     = "NOT_PRICED"
        status_name     = "Price not available"
        inactive_reason = "Title not found in Books Title Master"
        sage_title      = title
        last_active     = ""
        edition         = ""

    result = {
        "item_no":         isbn,
        "unit_price":      inr_price,     # INR price for quote
        "orig_price":      orig_price,    # original USD/GBP price
        "orig_currency":   orig_currency, # original currency
        "currency":        "INR",         # quote always in INR
        "item_status":     item_status,
        "status_name":     status_name,
        "inactive_reason": inactive_reason,
        "sage_title":      sage_title,
        "last_active":     last_active,
        "edition":         edition,
    }

    print(
        f"  [BC Items] Found: {title[:35]} "
        f"(ISBN: {isbn}, "
        f"Price: INR {inr_price:,.2f}"
        + (f" [{orig_currency} {orig_price}]"
           if orig_currency and orig_currency != "INR" else "")
        + f", Status: {item_status})"
    )

    return result