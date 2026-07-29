"""
bc_title_master.py
==================
Retrieves book pricing and status from Sage's BooksItem_BI
OData web service (Books Title Master).

Key fields:
  Sale_Price            — actual selling price
  Currency_Code         — explicit currency (may be blank)
  Gen_Prod_Posting_Group— used to derive currency when blank
  Active / Blocked      — item status
  Books_Status          — AVAI, OFPR etc.
  Status_Name           — human readable status
  Sage_Title            — main title
  Sage_Sub_Title        — subtitle (often empty in OData)
  Edition               — edition info
  Last_Date_Modified    — last change date

Public interface:
  get_title_price(isbn, title="") -> dict | None
"""

import re
import time
import requests
from bc_auth import get_bc_token
from bc_exchange_rates import convert as fx_convert
from config import BC_TENANT_ID, BC_ENVIRONMENT

COMPANY_ID = "ba6aaeee-d6d5-f011-8542-6045bd732afe"

ODATA_BASE = (
    f"https://api.businesscentral.dynamics.com/v2.0/"
    f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/ODataV4"
)

SERVICE_URL = f"{ODATA_BASE}/Company('{COMPANY_ID}')/BooksItem_BI"

POSTING_GROUP_CURRENCY = {
    "BK-USD-POD":    "USD",
    "BK-DOLLAR":     "USD",
    "BK-RUPEES":     "INR",
    "BK-POUND":      "GBP",
    "BK-EURO":       "EUR",
    "BK-USD":        "USD",
    "BK-RUPEES-POD": "INR",
}

STATUS_ACTIVE       = "ACTIVE"
STATUS_OUT_OF_PRINT = "OUT_OF_PRINT"
STATUS_BLOCKED      = "BLOCKED"
STATUS_UNKNOWN      = "UNKNOWN"

_price_cache = {}


def get_headers():
    token = get_bc_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json"
    }


# =============================================================
# Public Interface
# =============================================================

def get_title_price(isbn, title=""):
    """
    Returns full price and status for a book.
    Tries ISBN first, then title search.
    Returns None only if book is absent from BC entirely.
    """

    cache_key = isbn.strip() if isbn else title.strip().lower()
    if not cache_key:
        return None

    if cache_key in _price_cache:
        cached = _price_cache[cache_key]
        print(
            f"  [BC Price] Cache hit: "
            f"{cache_key[:20]} → "
            f"{cached.get('currency','')} "
            f"{cached.get('price',0)} "
            f"[{cached.get('status','')}]"
        )
        return cached

    if isbn and isbn.strip():
        result = _lookup_by_isbn(isbn.strip())
        if result:
            _price_cache[cache_key] = result
            return result

    if title and title.strip():
        result = _lookup_by_title(title.strip())
        if result:
            _price_cache[cache_key] = result
            return result

    print(f"  [BC Price] Not in BC catalogue: {cache_key[:40]}")
    return None


# =============================================================
# Lookup Functions
# =============================================================

def _lookup_by_isbn(isbn):
    """Look up by ISBN (No field)."""

    clean_isbn = isbn.replace("-", "").replace(" ", "").strip("/")
    print(f"  [BC Price] Looking up by ISBN: {clean_isbn}")

    try:
        r = requests.get(
            SERVICE_URL,
            headers=get_headers(),
            params={
                "$filter": f"No eq '{clean_isbn}'",
                "$top":    1
            },
            timeout=30
        )
        if r.ok:
            items = r.json().get("value", [])
            if items:
                return _parse_item(items[0])
    except Exception as e:
        print(f"  [BC Price] ISBN lookup error: {e}")

    return None


def _lookup_by_title(title):
    """
    Look up by title in BooksItem_BI.

    Note: Sage_Sub_Title is often empty in the OData API
    even though it shows in the BC UI. We rely on Sage_Title
    only for matching, using a two-word phrase for precision.

    Strategy:
      1. Exact match on Sage_Title
      2. Two-word phrase search (most specific)
      3. Single-word fallback with $top=100 and $orderby
    """

    print(f"  [BC Price] Looking up by title: {title[:40]}")

    def clean_words(text):
        cleaned = re.sub(r"[^a-zA-Z0-9 ]", " ", text)
        return set(w.lower() for w in cleaned.split() if len(w) > 3)

    customer_words = clean_words(title)

    # Step 1 — Exact match
    try:
        r = requests.get(
            SERVICE_URL,
            headers=get_headers(),
            params={
                "$filter": f"Sage_Title eq '{title}'",
                "$top":    1
            },
            timeout=30
        )
        if r.ok:
            items = r.json().get("value", [])
            if items:
                return _parse_item(items[0])
    except Exception as e:
        print(f"  [BC Price] Exact match error: {e}")

    # Get significant words
    sig_words = [
        w for w in re.sub(r"[^a-zA-Z0-9 ]", " ", title).split()
        if len(w) > 3
    ]

    if not sig_words:
        return None

    # Build search attempts
    search_attempts = []

    if len(sig_words) >= 2:
        two_word = f"{sig_words[0]} {sig_words[1]}"
        search_attempts.append((
            f"contains(Sage_Title, '{two_word}')", 20
        ))

    search_attempts.append((
        f"contains(Sage_Title, '{sig_words[0]}')", 100
    ))

    for filter_str, top_n in search_attempts:

        try:
            r = requests.get(
                SERVICE_URL,
                headers=get_headers(),
                params={
                    "$filter":  filter_str,
                    "$orderby": "Sage_Title asc",
                    "$top":     top_n,
                    "$select":  (
                        "No,Sage_Title,Sage_Sub_Title,Edition,"
                        "Sale_Price,Currency_Code,"
                        "Gen_Prod_Posting_Group,Active,Blocked,"
                        "Books_Status,Status_Name,"
                        "Last_Date_Modified,Publication_Date"
                    )
                },
                timeout=30
            )

            if not r.ok:
                continue

            items = r.json().get("value", [])
            if not items:
                continue

            print(
                f"  [BC Price] {len(items)} result(s) "
                f"for: {filter_str[:55]}"
            )

            best_match   = None
            best_overlap = 0

            for item in items:
                sage_title = (item.get("Sage_Title") or "").strip()
                sage_sub   = (item.get("Sage_Sub_Title") or "").strip()
                full_bc    = f"{sage_title} {sage_sub}".strip()
                bc_words   = clean_words(full_bc)
                overlap    = customer_words & bc_words

                if len(overlap) > best_overlap:
                    best_overlap = len(overlap)
                    best_match   = item

            if best_match and best_overlap >= 2:
                sage_title = (best_match.get("Sage_Title") or "").strip()
                sage_sub   = (best_match.get("Sage_Sub_Title") or "").strip()
                display    = (
                    f"{sage_title}: {sage_sub}"
                    if sage_sub else sage_title
                )
                print(
                    f"  [BC Price] Matched: '{display[:55]}' "
                    f"(overlap: {best_overlap} words)"
                )
                return _parse_item(best_match)

            print(
                f"  [BC Price] No confident match "
                f"(best: {best_overlap}) — trying next..."
            )

        except Exception as e:
            print(f"  [BC Price] Search error: {e}")

    print(f"  [BC Price] Not found by title: {title[:40]}")
    return None


# =============================================================
# Item Parsing
# =============================================================

def _derive_currency(item):
    """Derives currency from Currency_Code or posting group."""

    currency = (item.get("Currency_Code") or "").strip()
    if currency:
        return currency

    posting_group = (item.get("Gen_Prod_Posting_Group") or "").strip()
    return POSTING_GROUP_CURRENCY.get(posting_group, "INR")


def _determine_status(item):
    """Determines business status of an item."""

    active        = item.get("Active", True)
    blocked       = item.get("Blocked", False)
    books_status  = (item.get("Books_Status") or "").strip()
    status_name   = (item.get("Status_Name") or "").strip()
    edition       = (item.get("Edition") or "").strip()
    sale_price    = float(item.get("Sale_Price") or 0)
    last_modified = (item.get("Last_Date_Modified") or "")[:10]

    sage_title = (item.get("Sage_Title") or "").strip()
    sage_sub   = (item.get("Sage_Sub_Title") or "").strip()
    full_title = f"{sage_title}: {sage_sub}" if sage_sub else sage_title

    if active and not blocked:
        return {
            "status":      STATUS_ACTIVE,
            "status_name": status_name or "Available",
            "reason":      None,
            "last_active": last_modified,
            "edition":     edition,
            "sage_title":  full_title,
            "price":       sale_price,
        }

    if blocked and books_status == "AVAI":
        reason = (
            f"This edition ({edition}) is blocked for new sales "
            f"as it has likely been superseded by a newer edition. "
            f"Last price on record: {sale_price}. "
            f"Last updated: {last_modified}. "
            f"Please check with Sage for the current edition."
        )
        return {
            "status":      STATUS_BLOCKED,
            "status_name": "Edition Superseded",
            "reason":      reason,
            "last_active": last_modified,
            "edition":     edition,
            "sage_title":  full_title,
            "price":       sale_price,
        }

    if not active and books_status == "OFPR":
        reason = (
            f"This title is Out of Print. "
            f"Last known price: {sale_price}. "
            f"Last updated: {last_modified}."
        )
        return {
            "status":      STATUS_OUT_OF_PRINT,
            "status_name": "Out of Print",
            "reason":      reason,
            "last_active": last_modified,
            "edition":     edition,
            "sage_title":  full_title,
            "price":       sale_price,
        }

    reason = (
        f"Item inactive. Status: {books_status} ({status_name}). "
        f"Last updated: {last_modified}."
    )
    return {
        "status":      STATUS_UNKNOWN,
        "status_name": status_name or "Inactive",
        "reason":      reason,
        "last_active": last_modified,
        "edition":     edition,
        "sage_title":  full_title,
        "price":       sale_price,
    }


def _parse_item(item):
    """Parses a BooksItem_BI record into a standardised result dict."""

    currency     = _derive_currency(item)
    status_info  = _determine_status(item)
    sale_price   = status_info["price"]

    inr_price = fx_convert(sale_price, currency, "INR")

    result = {
        "price":       sale_price,
        "inr_price":   inr_price,
        "currency":    currency,
        "status":      status_info["status"],
        "status_name": status_info["status_name"],
        "reason":      status_info["reason"],
        "last_active": status_info["last_active"],
        "edition":     status_info["edition"],
        "sage_title":  status_info["sage_title"],
        "isbn":        item.get("No", ""),
    }

    status_label = status_info["status"]
    print(
        f"  [BC Price] Found: {item.get('No','')} | "
        f"{status_info['sage_title'][:30]} | "
        f"{currency} {sale_price}"
        + (f" = INR {inr_price:,.2f}" if currency != "INR" else "")
        + f" | [{status_label}]"
    )

    if status_info["reason"]:
        print(f"  [BC Price] ⚠  {status_info['reason'][:80]}")

    return result


def clear_cache():
    """Clears the price cache."""
    _price_cache.clear()


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("BC BOOKS TITLE MASTER — FULL TEST")
    print("=" * 60)

    test_cases = [
        ("9789386062741", "An Introduction to Qualitative Research"),
        ("9781446258965", "The Essential Guide to Doing Your Research Project"),
        ("9781412994279", "Criminal Investigation"),
        ("9781506363226", "The Law of Journalism and Mass Communication"),
        ("9781529669954", "Concepts in International Relations"),
        ("9781506336169", "Case Study Research and Applications"),
        ("9780761910855", "Research Design"),
        ("9781506347561", "Introduction to Criminology: Why Do They Do It"),
        ("9781412979719", "Introduction to Criminology: Theories"),
        ("9781446256091", "Criminology: The Essentials"),
        ("9780748409518", "Professional Issues in Software Engineering"),
        ("",              "Effective Training Systems, Strategies, and Practices"),
    ]

    active    = 0
    inactive  = 0
    not_found = 0

    for isbn, title in test_cases:
        print(f"\n  {'—'*50}")
        print(f"  {title[:50]}")
        result = get_title_price(isbn, title)
        if result:
            if result["status"] == STATUS_ACTIVE:
                active += 1
            else:
                inactive += 1
        else:
            not_found += 1

    print(f"\n{'='*60}")
    print(f"Active: {active} | Inactive: {inactive} | Not found: {not_found}")
    print(f"{'='*60}")