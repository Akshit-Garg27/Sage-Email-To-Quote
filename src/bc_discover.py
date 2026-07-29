"""
bc_discover.py
==============
Discovers all available API endpoints for your BC company.

This script calls the BC API metadata endpoint and lists
every entity set available — telling us exactly what data
can be accessed via the standard BC API.

Run from src/ directory:
  python bc_discover.py

Output shows:
  - All available entity sets (customers, items, vendors etc.)
  - Which ones are accessible with current permissions
  - Exact endpoint names to use in bc_customer.py / bc_items.py
"""

import requests
import json
from bc_auth import get_bc_token
from config import BC_TENANT_ID, BC_ENVIRONMENT, BC_COMPANY_ID


COMPANY_ID = BC_COMPANY_ID or "ba6aaeee-d6d5-f011-8542-6045bd732afe"

BASE_URL = (
    f"https://api.businesscentral.dynamics.com/v2.0/"
    f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/api/v2.0"
)


def get_headers():
    token = get_bc_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }


# =============================================================
# Test 1 — List All Entity Sets (API Metadata)
# =============================================================

def discover_entity_sets():

    print("\n" + "=" * 60)
    print("  TEST 1 — API ENTITY SETS")
    print("  What endpoints are available?")
    print("=" * 60)

    url = f"{BASE_URL}/$metadata"

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )

        print(f"\n  HTTP Status: {response.status_code}")

        if response.ok:
            # Metadata is XML — extract entity set names
            text = response.text
            entity_sets = []

            # Find all EntitySet Name= entries
            import re
            matches = re.findall(
                r'EntitySet Name="([^"]+)"',
                text
            )

            if matches:
                print(f"\n  Found {len(matches)} entity sets:\n")
                for name in sorted(matches):
                    print(f"    → {name}")
            else:
                print("\n  Could not parse entity sets from metadata")
                print(f"  Raw response (first 500 chars):")
                print(f"  {text[:500]}")

        else:
            print(f"  Failed: {response.text[:300]}")

    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")


# =============================================================
# Test 2 — Direct Company Endpoint Test
# =============================================================

def test_company_endpoint():

    print("\n" + "=" * 60)
    print("  TEST 2 — COMPANY ENDPOINT")
    print("=" * 60)

    url = f"{BASE_URL}/companies({COMPANY_ID})"

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )

        print(f"\n  HTTP Status: {response.status_code}")

        if response.ok:
            data = response.json()
            print(f"  Company Name : {data.get('displayName')}")
            print(f"  Company ID   : {data.get('id')}")
        else:
            print(f"  Failed: {response.text[:300]}")

    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")


# =============================================================
# Test 3 — Test Standard Endpoints
# =============================================================

def test_standard_endpoints():

    print("\n" + "=" * 60)
    print("  TEST 3 — STANDARD ENDPOINT ACCESS")
    print("  Testing each endpoint individually")
    print("=" * 60)

    endpoints = [
        ("customers",              "Customer list"),
        ("items",                  "Item/Product list"),
        ("vendors",                "Vendor list"),
        ("salesOrders",            "Sales Orders"),
        ("salesQuotes",            "Sales Quotes"),
        ("salesInvoices",          "Sales Invoices"),
        ("purchaseOrders",         "Purchase Orders"),
        ("contacts",               "Contacts"),
        ("currencies",             "Currencies"),
        ("paymentTerms",           "Payment Terms"),
        ("units Of Measure",       "Units of Measure"),
        ("itemCategories",         "Item Categories"),
        ("accounts",               "Chart of Accounts"),
        ("journals",               "Journals"),
        ("employees",              "Employees"),
        ("projects",               "Projects"),
        ("shipmentMethods",        "Shipment Methods"),
        ("countriesRegions",       "Countries/Regions"),
    ]

    results = []

    for endpoint, description in endpoints:

        url = (
            f"{BASE_URL}/companies({COMPANY_ID})/"
            f"{endpoint}?$top=1"
        )

        try:
            response = requests.get(
                url,
                headers=get_headers(),
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                count = len(data.get("value", []))
                status = f"✓ ACCESSIBLE  (returned {count} record(s))"
                results.append((endpoint, True, count))

            elif response.status_code == 401:
                status = "✗ UNAUTHORIZED"
                results.append((endpoint, False, 0))

            elif response.status_code == 403:
                status = "✗ FORBIDDEN (no permission)"
                results.append((endpoint, False, 0))

            elif response.status_code == 404:
                status = "✗ NOT FOUND (endpoint does not exist)"
                results.append((endpoint, False, 0))

            else:
                status = f"✗ HTTP {response.status_code}"
                results.append((endpoint, False, 0))

        except Exception as e:
            status = f"✗ ERROR: {type(e).__name__}"
            results.append((endpoint, False, 0))

        print(f"\n  {description}")
        print(f"  Endpoint : /{endpoint}")
        print(f"  Result   : {status}")

    return results


# =============================================================
# Test 4 — Sample Customer Data
# =============================================================

def sample_customer_data():

    print("\n" + "=" * 60)
    print("  TEST 4 — SAMPLE CUSTOMER DATA")
    print("  First 5 customers in BC")
    print("=" * 60)

    url = (
        f"{BASE_URL}/companies({COMPANY_ID})/"
        f"customers?$top=5"
        f"&$select=number,displayName,currencyCode,country"
    )

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )

        if response.ok:
            customers = response.json().get("value", [])

            if customers:
                print(f"\n  Found {len(customers)} customers:\n")
                for c in customers:
                    print(
                        f"    No      : {c.get('number', 'N/A')}"
                    )
                    print(
                        f"    Name    : {c.get('displayName', 'N/A')}"
                    )
                    print(
                        f"    Currency: {c.get('currencyCode', 'INR (local)')}"
                    )
                    print(
                        f"    Country : {c.get('country', 'N/A')}"
                    )
                    print()
            else:
                print("\n  No customers returned")

        else:
            print(f"\n  Failed: {response.text[:300]}")

    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")


# =============================================================
# Test 5 — Sample Items Data
# =============================================================

def sample_items_data():

    print("\n" + "=" * 60)
    print("  TEST 5 — SAMPLE ITEMS DATA")
    print("  First 5 items in BC")
    print("=" * 60)

    url = (
        f"{BASE_URL}/companies({COMPANY_ID})/"
        f"items?$top=5"
        f"&$select=number,displayName,unitPrice,type"
    )

    try:
        response = requests.get(
            url,
            headers=get_headers(),
            timeout=30
        )

        if response.ok:
            items = response.json().get("value", [])

            if items:
                print(f"\n  Found {len(items)} items:\n")
                for item in items:
                    print(
                        f"    No         : {item.get('number', 'N/A')}"
                    )
                    print(
                        f"    Description: {item.get('displayName', 'N/A')}"
                    )
                    print(
                        f"    Unit Price : {item.get('unitPrice', 'N/A')}"
                    )
                    print(
                        f"    Type       : {item.get('type', 'N/A')}"
                    )
                    print()
            else:
                print("\n  No items returned")
                print(
                    "  This may mean items are in a custom table"
                    " (e.g. Series Master / TableData 50025)"
                )

        else:
            print(f"\n  Failed: HTTP {response.status_code}")
            print(f"  {response.text[:300]}")

    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")


# =============================================================
# Test 6 — Custom API Pages
# =============================================================

def test_custom_endpoints():

    print("\n" + "=" * 60)
    print("  TEST 6 — CUSTOM SAGE API PAGES")
    print("  Testing Sage-specific custom endpoints")
    print("=" * 60)

    # Common custom endpoint patterns for publishing companies
    custom_endpoints = [
        "seriesMasters",
        "series",
        "journals",
        "publications",
        "subscriptions",
        "products",
        "titles",
        "journalItems",
        "salesItems",
    ]

    for endpoint in custom_endpoints:

        url = (
            f"{BASE_URL}/companies({COMPANY_ID})/"
            f"{endpoint}?$top=1"
        )

        try:
            response = requests.get(
                url,
                headers=get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                count = len(data.get("value", []))
                print(f"\n  ✓ FOUND: /{endpoint}")
                print(f"    Records returned: {count}")
                if count > 0:
                    first = data["value"][0]
                    keys = list(first.keys())[:5]
                    print(f"    Fields: {keys}")

            elif response.status_code == 404:
                print(f"  ✗ NOT FOUND: /{endpoint}")

            else:
                print(
                    f"  ? /{endpoint} → "
                    f"HTTP {response.status_code}"
                )

        except Exception as e:
            print(f"  ✗ /{endpoint} → Error: {e}")


# =============================================================
# Summary
# =============================================================

def print_summary(results):

    print("\n" + "=" * 60)
    print("  SUMMARY — ACCESSIBLE ENDPOINTS")
    print("=" * 60)

    accessible = [r for r in results if r[1]]
    blocked = [r for r in results if not r[1]]

    print(f"\n  Accessible ({len(accessible)}):")
    for endpoint, _, count in accessible:
        print(f"    ✓ /{endpoint} ({count} record(s))")

    print(f"\n  Not accessible ({len(blocked)}):")
    for endpoint, _, _ in blocked:
        print(f"    ✗ /{endpoint}")


# =============================================================
# Run All Tests
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  BC API DISCOVERY")
    print(f"  Company ID  : {COMPANY_ID}")
    print(f"  Environment : {BC_ENVIRONMENT}")
    print("=" * 60)

    discover_entity_sets()
    test_company_endpoint()
    results = test_standard_endpoints()
    sample_customer_data()
    sample_items_data()
    test_custom_endpoints()
    print_summary(results)

    print("\n" + "=" * 60)
    print("  Discovery complete.")
    print("  Use results above to configure bc_items.py")
    print("=" * 60 + "\n")