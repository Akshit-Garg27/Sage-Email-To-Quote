"""
test_bc_integration.py
======================
End-to-end test for the Business Central integration layer.

Uses real Sage Publications data from BC Sandbox.

Run from src/ directory:
  python test_bc_integration.py
"""

import sys
import bc_cache


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(passed, detail=""):
    status = "PASS ✓" if passed else "FAIL ✗"
    print(f"  Result : {status}")
    if detail:
        print(f"  Detail : {detail}")


# =============================================================
# Test 1 — Authentication
# =============================================================

def test_auth():

    print_header("TEST 1 — Authentication")

    try:
        from bc_auth import get_bc_token

        token = get_bc_token()
        passed = bool(token) and len(token) > 20
        print_result(passed, f"Token: {token[:40]}...")

        print("\n  Testing cache...")
        token2 = get_bc_token()
        print(f"  Cache working: {token == token2}")

        return passed

    except Exception as e:
        print_result(False, f"{type(e).__name__}: {e}")
        return False


# =============================================================
# Test 2 — Company Discovery
# =============================================================

def test_company():

    print_header("TEST 2 — Company Discovery")

    try:
        from bc_company import get_company_id

        company_id = get_company_id()
        passed = bool(company_id) and len(company_id) > 10
        print_result(passed, f"Company ID: {company_id}")
        return passed

    except Exception as e:
        print_result(False, f"{type(e).__name__}: {e}")
        return False


# =============================================================
# Test 3 — Customer Lookup (Real Sage Data)
# =============================================================

def test_customers():

    print_header("TEST 3 — Customer Lookup (Real Sage BC Data)")

    from bc_customer import get_customer

    # Clear cache to ensure fresh BC API calls
    bc_cache.clear()
    print("  Cache cleared for fresh lookup.")

    results = []

    # Test A — real Sage customer
    print("\n  3A: CENTRAL NEWS AGENCY")
    customer = get_customer("CENTRAL NEWS AGENCY")

    if customer:
        passed = all(
            k in customer
            for k in ["customer_id", "currency", "country"]
        )
        print(f"  Found    : {customer}")
        print_result(passed)
    else:
        passed = False
        print_result(False, "Not found in BC")

    results.append(passed)

    # Test B — second real customer
    print("\n  3B: SURIYA BOOKSHOP, SOCIAL SCIENTISTS")
    customer = get_customer("SURIYA BOOKSHOP, SOCIAL SCIENTISTS")

    if customer:
        passed = all(
            k in customer
            for k in ["customer_id", "currency", "country"]
        )
        print(f"  Found    : {customer}")
        print_result(passed)
    else:
        passed = False
        print_result(False, "Not found in BC")

    results.append(passed)

    # Test C — unknown customer
    print("\n  3C: Unknown customer — should return None")
    result = get_customer("UNKNOWN ORGANISATION XYZ")
    passed = result is None
    print_result(passed, f"Returned: {result}")
    results.append(passed)

    # Test D — case insensitive
    print("\n  3D: Lowercase — should still find customer")
    result = get_customer("central news agency")
    passed = result is not None
    print_result(passed, f"Returned: {result}")
    results.append(passed)

    # Test E — empty string
    print("\n  3E: Empty string — should return None safely")
    result = get_customer("")
    passed = result is None
    print_result(passed, f"Returned: {result}")
    results.append(passed)

    return all(results)


# =============================================================
# Test 4 — Items Lookup (Real Sage Data)
# =============================================================

def test_items():

    print_header("TEST 4 — Items Lookup (Real Sage BC Data)")

    from bc_items import get_product

    results = []

    # Test A — real Sage book title
    print("\n  4A: Coping with Life Stress")
    product = get_product("Coping with Life Stress")

    if product:
        passed = "item_no" in product
        print(f"  Found : {product}")
        print_result(passed)
    else:
        passed = False
        print_result(
            False,
            "Not found — note: BC items have 0 unit price, "
            "prices are at sales order level"
        )

    results.append(passed)

    # Test B — second real title
    print("\n  4B: Performance Management")
    product = get_product("Performance Management")

    if product:
        passed = "item_no" in product
        print(f"  Found : {product}")
        print_result(passed)
    else:
        passed = False
        print_result(False, "Not found in BC")

    results.append(passed)

    # Test C — unknown product
    print("\n  4C: Unknown product — should return None")
    result = get_product("Nonexistent Book XYZ 99999")
    passed = result is None
    print_result(passed, f"Returned: {result}")
    results.append(passed)

    return all(results)


# =============================================================
# Test 5 — validate_products() Full Interface
# =============================================================

def test_validate_products():

    print_header("TEST 5 — validate_products() Full Interface")

    from bc_items import validate_products

    products = [
        {"name": "Coping with Life Stress",    "quantity": 5},
        {"name": "Performance Management",      "quantity": 10},
        {"name": "Unknown Book XYZ",            "quantity": 3},
    ]

    validated, missing = validate_products(products)

    print(f"\n  Validated : {len(validated)}")
    for v in validated:
        print(
            f"    {v['requested']['name']} "
            f"× {v['requested']['quantity']} "
            f"→ {v['master_data']}"
        )

    print(f"\n  Missing   : {missing}")

    passed = (
        len(validated) == 2 and
        len(missing) == 1 and
        missing[0] == "Unknown Book XYZ"
    )

    print_result(passed)
    return passed


# =============================================================
# Test 6 — Cache Behaviour
# =============================================================

def test_cache():

    print_header("TEST 6 — Cache Behaviour")

    from bc_customer import get_customer

    print("\n  Clearing cache...")
    bc_cache.clear()

    print("\n  First lookup (hits BC API)...")
    c1 = get_customer("CENTRAL NEWS AGENCY")

    print("\n  Second lookup (uses cache)...")
    c2 = get_customer("CENTRAL NEWS AGENCY")

    passed = c1 == c2
    print(f"\n  Results match: {passed}")
    print_result(passed)

    return passed


# =============================================================
# Run All Tests
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  BC INTEGRATION TEST SUITE")
    print("  Sage Publications India Pvt. Ltd")
    print("  Sandbox_Sumit")
    print("=" * 60)

    tests = [
        ("Authentication",         test_auth),
        ("Company Discovery",      test_company),
        ("Customer Lookup",        test_customers),
        ("Items Lookup",           test_items),
        ("validate_products()",    test_validate_products),
        ("Cache Behaviour",        test_cache),
    ]

    results = {}

    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"\n  UNEXPECTED ERROR in {name}: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    all_passed = True

    for name, passed in results.items():
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n  All tests passed.")
        print("  Set BC_MODE=live in .env to activate.")
    else:
        print("\n  Some tests failed.")
        print("  Check output above for details.")

    sys.exit(0 if all_passed else 1)