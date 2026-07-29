"""
bc_cache.py
===========
In-memory cache for Business Central integration.

Caches:
  1. OAuth access token     — valid for 3600s (reuse until expiry)
  2. Company ID             — changes rarely, cache indefinitely per session
  3. Customer records       — cache for CUSTOMER_TTL seconds
  4. Product/Item records   — cache for PRODUCT_TTL seconds

All cache is in-memory only.
Cache is cleared when the Python process restarts.
No Redis, no file serialisation — appropriate for single-process prototype.
"""

import time


# =============================================================
# Cache TTL Settings (seconds)
# =============================================================

CUSTOMER_TTL = 900    # 15 minutes
PRODUCT_TTL = 900     # 15 minutes


# =============================================================
# Internal Cache Store
# =============================================================

_cache = {

    "token": {
        "value": None,
        "expires_at": 0
    },

    "company_id": None,

    "customers": {},   # key: normalised name, value: {record, cached_at}

    "products": {}     # key: normalised name, value: {record, cached_at}

}


# =============================================================
# Token Cache
# =============================================================

def get_token():
    """
    Returns cached token if still valid. None if expired or missing.
    Tokens are considered expired 60 seconds early as a safety buffer.
    """

    token = _cache["token"]

    if token["value"] and time.time() < token["expires_at"] - 60:
        return token["value"]

    return None


def set_token(value, expires_in=3600):
    """
    Stores a new token with its expiry time.
    expires_in is the lifetime in seconds returned by the token endpoint.
    """

    _cache["token"]["value"] = value
    _cache["token"]["expires_at"] = time.time() + expires_in

    print(
        f"  [BC Cache] Token cached. "
        f"Expires in {expires_in}s."
    )


# =============================================================
# Company ID Cache
# =============================================================

def get_company_id():
    """
    Returns cached company ID. None if not yet discovered.
    Company ID is stable for the session — no TTL needed.
    """
    return _cache["company_id"]


def set_company_id(company_id):
    """
    Stores the company ID for the session.
    """
    _cache["company_id"] = company_id
    print(f"  [BC Cache] Company ID cached: {company_id}")


# =============================================================
# Customer Cache
# =============================================================

def get_customer(name_key):
    """
    Returns cached customer lookup result for name_key.

    Returns:
      _MISS  → key not in cache, caller must hit BC API
      None   → key in cache, confirmed not found in BC
      dict   → key in cache, customer record found
    """

    entry = _cache["customers"].get(name_key)

    if entry is None:
        return _MISS

    if not _is_valid(entry["cached_at"], CUSTOMER_TTL):
        return _MISS

    return entry["record"]


def set_customer(name_key, record):
    """
    Stores a customer record in cache.
    record can be a dict (found) or None (confirmed not found).
    Both are cached to avoid repeat lookups for unknown customers.
    """

    _cache["customers"][name_key] = {
        "record": record,
        "cached_at": time.time()
    }


# =============================================================
# Product Cache
# =============================================================

def get_product(name_key):
    """
    Returns cached product record for the given name key.
    Returns None if not cached or TTL expired.
    Distinguishes between cache miss and cached None:
      - Key not in cache → returns sentinel _MISS
      - Key in cache with None → confirmed not found, returns None
      - Key in cache with record → returns record
    """

    entry = _cache["products"].get(name_key)

    if entry is None:
        return _MISS

    if _is_valid(entry["cached_at"], PRODUCT_TTL):
        return entry["record"]

    return _MISS


def set_product(name_key, record):
    """
    Stores a product record in cache.
    record can be a dict (found) or None (confirmed not found).
    """

    _cache["products"][name_key] = {
        "record": record,
        "cached_at": time.time()
    }


# =============================================================
# Utilities
# =============================================================

class _CacheMiss:
    """Sentinel value to distinguish cache miss from cached None."""
    pass


_MISS = _CacheMiss()


def _is_valid(cached_at, ttl):
    """Returns True if the cached entry is still within its TTL."""
    return (time.time() - cached_at) < ttl


def clear():
    """
    Clears all cached data.
    Used in testing to ensure a clean state between test runs.
    """

    _cache["token"]["value"] = None
    _cache["token"]["expires_at"] = 0
    _cache["company_id"] = None
    _cache["customers"].clear()
    _cache["products"].clear()

    print("  [BC Cache] Cache cleared.")
