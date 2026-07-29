"""
bc_customer.py
==============
Customer lookup against Business Central Customers API.

Public interface identical to mock_bc.get_customer():
  get_customer(organization) → dict | None
"""

import requests
from bc_auth import get_bc_token
from bc_company import get_company_id
from bc_errors import BCAPIError, BCNetworkError, retry_with_backoff
from config import BC_TENANT_ID, BC_ENVIRONMENT

# Import cache module and keep reference
import bc_cache


# =============================================================
# BC API URL
# =============================================================

def _customers_url(company_id):
    return (
        f"https://api.businesscentral.dynamics.com/v2.0/"
        f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/api/v2.0/"
        f"companies({company_id})/customers"
    )


# =============================================================
# Public Interface
# =============================================================

def get_customer(organization):
    """
    Looks up a customer in BC by organisation name.

    Returns:
      dict  — customer found
      None  — customer not found in BC

    Raises nothing — all errors caught internally.
    """

    if not organization or not organization.strip():
        return None

    name_key = organization.strip().lower()

    # Check cache
    cached = bc_cache.get_customer(name_key)

    if not isinstance(cached, bc_cache._CacheMiss):
        if cached:
            print(f"  [BC Customer] Cache hit: '{organization}'")
        else:
            print(
                f"  [BC Customer] Cache hit (not found): '{organization}'"
            )
        return cached

    # Fetch from BC
    print(f"  [BC Customer] Looking up: '{organization}'")

    try:
        result = retry_with_backoff(
            lambda: _fetch_customer(organization, name_key)
        )
        bc_cache.set_customer(name_key, result)
        return result

    except Exception as e:
        print(f"  [BC Customer] ERROR: {type(e).__name__}: {e}")
        return None


# =============================================================
# Internal Fetch
# =============================================================

def _fetch_customer(organization, name_key):
    """
    Calls BC Customers API with OData filter on displayName.
    """

    token = get_bc_token()
    company_id = get_company_id()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    filter_query = f"tolower(displayName) eq '{name_key}'"

    params = {
        "$filter": filter_query,
        "$select": "id,number,displayName,currencyCode,country",
        "$top": 1
    }

    url = _customers_url(company_id)

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

    except requests.exceptions.Timeout:
        raise BCNetworkError("Customer lookup timed out.")

    except requests.exceptions.ConnectionError:
        raise BCNetworkError("Cannot connect to BC API.")

    if response.status_code == 401:
        raise BCAPIError("Unauthorized. Token may have expired.")

    if not response.ok:
        raise BCAPIError(
            f"Customer lookup failed. "
            f"HTTP {response.status_code}: {response.text}"
        )

    data = response.json()
    customers = data.get("value", [])

    if not customers:
        print(f"  [BC Customer] Not found: '{organization}'")
        return None

    customer = customers[0]

    # Sage Publications BC returns blank currencyCode
    # for local currency — default to INR
    currency = customer.get("currencyCode", "")
    if not currency:
        currency = "INR"

    result = {
        "customer_id": customer.get("number", ""),
        "currency":    currency,
        "country":     customer.get("country", "")
    }

    print(
        f"  [BC Customer] Found: {customer.get('displayName')} "
        f"(ID: {result['customer_id']})"
    )

    return result


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("BC CUSTOMER — LOOKUP TEST")
    print("=" * 60)

    # Clear cache before testing
    bc_cache.clear()
    print("Cache cleared for fresh test.\n")

    test_cases = [
        ("CENTRAL NEWS AGENCY",
         "Should be found"),
        ("SURIYA BOOKSHOP, SOCIAL SCIENTISTS",
         "Should be found"),
        ("NATIONAL INSTITUTE OF PUBLIC COOPERATION",
         "Should be found"),
        ("Unknown Company XYZ",
         "Should return None"),
        ("central news agency",
         "Lowercase — should be found"),
    ]

    for name, description in test_cases:

        print(f"  Test: {name} ({description})")
        result = get_customer(name)

        if result:
            print(f"  Found   : {result}")
        else:
            print(f"  Result  : None (not found)")

        print()

    print("=" * 60)
    print("Testing cache — repeat lookup...")
    print("=" * 60)

    result = get_customer("CENTRAL NEWS AGENCY")
    print(f"  Cached result: {result}")