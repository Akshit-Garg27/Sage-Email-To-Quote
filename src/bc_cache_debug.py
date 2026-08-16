"""
bc_cache_debug.py
=================
Diagnose the cache module identity problem.
"""

import sys
import os

# Print Python path
print("\nPython Path:")
for p in sys.path:
    print(f"  {p}")

# Import bc_cache and check its identity
import bc_cache
print(f"\nbc_cache location: {bc_cache.__file__}")
print(f"bc_cache id: {id(bc_cache)}")

# Set a value
bc_cache.set_token("TEST_TOKEN_123", 3600)
print(f"Set token in bc_cache id={id(bc_cache)}")

# Import bc_customer and check what bc_cache it uses
import bc_customer
print(f"\nbc_customer location: {bc_customer.__file__}")

# Check if bc_customer's bc_cache is same instance
import importlib
bc_cache_in_customer = sys.modules.get('bc_cache')
print(f"bc_cache in sys.modules id: {id(bc_cache_in_customer)}")

# Try getting token through customer's cache
token = bc_cache.get_token()
print(f"\nToken from bc_cache: {'SET' if token else 'EMPTY'}")

# Clear and check
bc_cache.clear()
print("Cleared bc_cache")

token_after = bc_cache.get_token()
print(f"Token after clear: {'SET' if token_after else 'EMPTY'}")

print("\nAll sys.modules containing 'cache':")
for key in sys.modules:
    if 'cache' in key.lower():
        print(f"  {key}: {id(sys.modules[key])}")