"""
bc_verify.py
============
Verifies bc_cache.py has the correct _MISS logic
and that bc_customer.py uses isinstance check.
"""

import sys
import os

src_path = r"c:\Users\agarg2\Documents\Email_to_Quote_AI\src"

# Check bc_cache.py content
cache_file = os.path.join(src_path, "bc_cache.py")
customer_file = os.path.join(src_path, "bc_customer.py")

print("=" * 60)
print("VERIFYING FILE CONTENTS")
print("=" * 60)

print(f"\nChecking: bc_cache.py")
with open(cache_file, 'r') as f:
    content = f.read()

checks = {
    "Has _CacheMiss class":     "class _CacheMiss" in content,
    "get_customer returns _MISS": "return _MISS" in content and "def get_customer" in content,
    "Has clear() function":     "def clear():" in content,
}

for check, result in checks.items():
    status = "✓" if result else "✗ MISSING"
    print(f"  {status}  {check}")

print(f"\nChecking: bc_customer.py")
with open(customer_file, 'r') as f:
    content = f.read()

checks2 = {
    "Uses import bc_cache":          "import bc_cache" in content,
    "Uses isinstance check":         "isinstance" in content,
    "Uses bc_cache._CacheMiss":      "_CacheMiss" in content,
    "No from bc_cache import":       "from bc_cache import" not in content,
}

for check, result in checks2.items():
    status = "✓" if result else "✗ MISSING"
    print(f"  {status}  {check}")

print("\n" + "=" * 60)
print("SHOWING get_customer() in bc_cache.py")
print("=" * 60)

# Extract and show the get_customer function
cache_file2 = open(cache_file).read()
start = cache_file2.find("def get_customer(")
end = cache_file2.find("\ndef set_customer(")
print(cache_file2[start:end])

print("\n" + "=" * 60)
print("SHOWING cache check in bc_customer.py")
print("=" * 60)

customer_content = open(customer_file).read()
start = customer_content.find("    # Check cache")
end = customer_content.find("    # Fetch from BC")
print(customer_content[start:end])