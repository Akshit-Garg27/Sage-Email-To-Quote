"""
bc_company.py
=============
Resolves and caches the Business Central Company ID.

The Company ID (GUID) is required as a path parameter
in all BC API calls:
  /v2.0/{tenant}/{environment}/api/v2.0/companies({company_id})/customers

Resolution order:
  1. BC_COMPANY_ID in .env  — explicit, always wins, no API call
  2. BC Cache               — already discovered this session
  3. BC API /companies      — discover automatically, then cache

Single responsibility: return a valid Company ID string.
"""

import requests
from config import BC_TENANT_ID, BC_ENVIRONMENT, BC_COMPANY_ID
from bc_auth import get_bc_token
from bc_errors import BCAPIError, BCNetworkError, BCNotFoundError, retry_with_backoff
from bc_cache import get_company_id as cache_get_company_id
from bc_cache import set_company_id as cache_set_company_id


# =============================================================
# BC API Base URL
# =============================================================

def _base_url():
    return (
        f"https://api.businesscentral.dynamics.com/v2.0/"
        f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/api/v2.0"
    )


# =============================================================
# Public Interface
# =============================================================

def get_company_id():
    """
    Returns the BC Company ID GUID.

    Checks .env first, then cache, then discovers via API.

    Raises:
      BCNotFoundError — no companies found in environment
      BCAPIError      — unexpected API response
      BCNetworkError  — cannot reach BC API
    """

    # Option 1 — explicitly set in .env
    if BC_COMPANY_ID:
        print(f"  [BC Company] Using Company ID from .env")
        return BC_COMPANY_ID

    # Option 2 — already cached this session
    cached = cache_get_company_id()

    if cached:
        print(f"  [BC Company] Using cached Company ID.")
        return cached

    # Option 3 — discover via API
    print("  [BC Company] Discovering Company ID via API...")

    return retry_with_backoff(_fetch_company_id)


def _fetch_company_id():
    """
    Calls the BC companies endpoint to discover the Company ID.
    Uses the first company returned — appropriate for single-company setups.
    """

    token = get_bc_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    url = f"{_base_url()}/companies"

    try:
        response = requests.get(url, headers=headers, timeout=30)

    except requests.exceptions.Timeout:
        raise BCNetworkError("BC API request timed out.")

    except requests.exceptions.ConnectionError:
        raise BCNetworkError("Cannot connect to BC API.")

    if not response.ok:
        raise BCAPIError(
            f"Companies endpoint failed. "
            f"HTTP {response.status_code}: {response.text}"
        )

    data = response.json()
    companies = data.get("value", [])

    if not companies:
        raise BCNotFoundError(
            f"No companies found in environment '{BC_ENVIRONMENT}'. "
            f"Check BC_ENVIRONMENT in .env."
        )

    # Use the first company
    company = companies[0]
    company_id = company.get("id")
    company_name = company.get("displayName", "Unknown")

    if not company_id:
        raise BCAPIError(
            "Company record missing 'id' field. "
            f"Response: {company}"
        )

    cache_set_company_id(company_id)

    print(
        f"  [BC Company] Found: {company_name} "
        f"(ID: {company_id})"
    )

    return company_id


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("BC COMPANY — DISCOVERY TEST")
    print("=" * 60)

    try:

        company_id = get_company_id()

        print(f"\n  Company ID : {company_id}")

        print("\n  Testing cache...")
        company_id_2 = get_company_id()

        if company_id == company_id_2:
            print("  Cache working correctly.")

        print("\n  Result: PASS")

    except Exception as e:
        print(f"\n  Result: FAIL")
        print(f"  Error : {type(e).__name__}: {e}")