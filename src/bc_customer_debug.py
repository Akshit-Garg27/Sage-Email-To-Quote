"""
bc_customer_debug.py
====================
Debug script to test customer lookup directly
against BC API without cache interference.
"""

import requests
from bc_auth import get_bc_token
from bc_company import get_company_id
from config import BC_TENANT_ID, BC_ENVIRONMENT

token = get_bc_token()
company_id = get_company_id()

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

base_url = (
    f"https://api.businesscentral.dynamics.com/v2.0/"
    f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/api/v2.0/"
    f"companies({company_id})/customers"
)

print("\n" + "=" * 60)
print("BC CUSTOMER DEBUG")
print("=" * 60)

# Test 1 — Get first 5 customers raw
print("\nTest 1 — First 5 customers (no filter):")
response = requests.get(
    base_url,
    headers=headers,
    params={
        "$top": 5,
        "$select": "number,displayName,currencyCode,country"
    },
    timeout=30
)

print(f"HTTP: {response.status_code}")
if response.ok:
    for c in response.json().get("value", []):
        print(f"  [{c.get('number')}] '{c.get('displayName')}' "
              f"| Currency: {c.get('currencyCode')} "
              f"| Country: {c.get('country')}")
else:
    print(f"Error: {response.text[:300]}")

# Test 2 — Filter by exact name
print("\nTest 2 — Filter by 'CENTRAL NEWS AGENCY':")
response = requests.get(
    base_url,
    headers=headers,
    params={
        "$filter": "displayName eq 'CENTRAL NEWS AGENCY'",
        "$select": "number,displayName,currencyCode,country",
        "$top": 1
    },
    timeout=30
)

print(f"HTTP: {response.status_code}")
if response.ok:
    results = response.json().get("value", [])
    print(f"Results: {len(results)}")
    for c in results:
        print(f"  {c}")
else:
    print(f"Error: {response.text[:300]}")

# Test 3 — Filter with tolower()
print("\nTest 3 — Filter with tolower():")
response = requests.get(
    base_url,
    headers=headers,
    params={
        "$filter": "tolower(displayName) eq 'central news agency'",
        "$select": "number,displayName,currencyCode,country",
        "$top": 1
    },
    timeout=30
)

print(f"HTTP: {response.status_code}")
if response.ok:
    results = response.json().get("value", [])
    print(f"Results: {len(results)}")
    for c in results:
        print(f"  {c}")
else:
    print(f"Error: {response.text[:300]}")

# Test 4 — Filter with contains
print("\nTest 4 — Filter with contains():")
response = requests.get(
    base_url,
    headers=headers,
    params={
        "$filter": "contains(displayName, 'CENTRAL')",
        "$select": "number,displayName,currencyCode,country",
        "$top": 3
    },
    timeout=30
)

print(f"HTTP: {response.status_code}")
if response.ok:
    results = response.json().get("value", [])
    print(f"Results: {len(results)}")
    for c in results:
        print(f"  {c}")
else:
    print(f"Error: {response.text[:300]}")

print("\n" + "=" * 60)