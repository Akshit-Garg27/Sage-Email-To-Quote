"""
bc_exchange_rates.py
====================
Exchange rate lookup using Sage Publications BC data.

Uses the standard BC v2.0 currencyExchangeRates endpoint
which Sage's finance team maintains directly in BC.

Rate structure in BC:
  exchangeRateAmount         : 1 (base amount in foreign currency)
  relationalExchangeRateAmount: 95.67 (equivalent in local currency INR)
  So: 1 USD = 95.67 INR

Caching:
  Rates cached in memory for RATE_CACHE_TTL seconds
  Default: 43200 seconds (12 hours — twice daily refresh)
  Cache cleared on process restart

Public interface:
  convert(amount, from_currency, to_currency="INR") → float
  get_rate(from_currency, to_currency="INR")        → float | None
  get_rate_info()                                   → dict (for display)
"""

import time
import requests
from bc_auth import get_bc_token
from config import BC_TENANT_ID, BC_ENVIRONMENT

COMPANY_ID = "ba6aaeee-d6d5-f011-8542-6045bd732afe"

BASE_URL = (
    f"https://api.businesscentral.dynamics.com/v2.0/"
    f"{BC_TENANT_ID}/{BC_ENVIRONMENT}/api/v2.0/"
    f"companies({COMPANY_ID})/currencyExchangeRates"
)

# Cache TTL — 12 hours (rates refresh twice per day)
RATE_CACHE_TTL = 43200

# In-memory cache
_rate_cache = {
    "rates":      {},   # {"USD": 95.67, "GBP": 106.21}
    "fetched_at": 0,    # Unix timestamp of last fetch
    "as_of_date": ""    # startingDate of most recent rate
}

# Local currency for Sage Publications India
LOCAL_CURRENCY = "INR"


def get_headers():
    token = get_bc_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json"
    }


# =============================================================
# Public Interface
# =============================================================

def convert(amount, from_currency, to_currency="INR"):
    """
    Converts an amount from one currency to another.

    Uses the most recent rate from BC.
    Returns the original amount unchanged if:
      - from_currency equals to_currency
      - rate not available in BC

    Args:
      amount       : float amount to convert
      from_currency: source currency code (USD, GBP, etc.)
      to_currency  : target currency code (default INR)

    Returns:
      float — converted amount
    """

    if not amount or amount == 0:
        return 0.0

    from_currency = (from_currency or "").strip().upper()
    to_currency   = (to_currency or "INR").strip().upper()

    # Same currency — no conversion needed
    if from_currency == to_currency:
        return float(amount)

    # Both are non-INR — convert via INR
    # from_currency → INR → to_currency
    if from_currency != LOCAL_CURRENCY and to_currency != LOCAL_CURRENCY:
        amount_inr = convert(amount, from_currency, LOCAL_CURRENCY)
        return convert(amount_inr, LOCAL_CURRENCY, to_currency)

    # Direct conversion: foreign → INR
    if to_currency == LOCAL_CURRENCY:
        rate = get_rate(from_currency)
        if rate:
            return round(float(amount) * rate, 2)
        print(
            f"  [FX] No rate for {from_currency} → {to_currency}, "
            f"using original amount"
        )
        return float(amount)

    # INR → foreign (less common but handle it)
    rate = get_rate(to_currency)
    if rate and rate > 0:
        return round(float(amount) / rate, 2)

    return float(amount)


def get_rate(from_currency, to_currency="INR"):
    """
    Returns the exchange rate: how many to_currency per 1 from_currency.
    Example: get_rate("USD") → 95.67 means 1 USD = 95.67 INR

    Returns None if rate not available.
    """

    from_currency = (from_currency or "").strip().upper()

    if from_currency == to_currency:
        return 1.0

    if from_currency == LOCAL_CURRENCY:
        return 1.0

    _ensure_rates_loaded()

    rate = _rate_cache["rates"].get(from_currency)

    if rate:
        return rate

    print(f"  [FX] Rate not available for {from_currency}")
    return None


def get_rate_info():
    """
    Returns current rate info dict for display purposes.

    Returns:
      {
        "rates":    {"USD": 95.67, "GBP": 106.21},
        "as_of":    "2026-06-27",
        "source":   "Business Central",
        "age_hours": 0.5
      }
    """

    _ensure_rates_loaded()

    age_hours = (
        (time.time() - _rate_cache["fetched_at"]) / 3600
        if _rate_cache["fetched_at"] > 0
        else 0
    )

    return {
        "rates":     dict(_rate_cache["rates"]),
        "as_of":     _rate_cache["as_of_date"],
        "source":    "Business Central",
        "age_hours": round(age_hours, 1)
    }


# =============================================================
# Rate Loading
# =============================================================

def _ensure_rates_loaded():
    """
    Loads rates from BC if cache is empty or expired.
    Called automatically by get_rate() and convert().
    """

    now = time.time()
    cache_age = now - _rate_cache["fetched_at"]

    if _rate_cache["rates"] and cache_age < RATE_CACHE_TTL:
        return  # Cache is fresh

    if _rate_cache["rates"]:
        print(
            f"  [FX] Rates cache expired "
            f"({cache_age/3600:.1f}h old). Refreshing..."
        )
    else:
        print("  [FX] Loading exchange rates from BC...")

    _fetch_all_rates()


def _fetch_all_rates():
    """
    Fetches the latest exchange rate for each currency from BC.
    BC stores one rate per currency per date — we want the most
    recent rate for each currency.
    """

    try:
        # Get all unique currency codes first
        r_currencies = requests.get(
            BASE_URL,
            headers=get_headers(),
            params={
                "$select": "currencyCode",
                "$orderby": "startingDate desc",
                "$top": 100
            },
            timeout=30
        )

        if not r_currencies.ok:
            print(f"  [FX] Failed to fetch currencies: "
                  f"HTTP {r_currencies.status_code}")
            return

        all_records = r_currencies.json().get("value", [])

        # Get unique currency codes
        currencies = list({
            r["currencyCode"]
            for r in all_records
            if r.get("currencyCode")
        })

        if not currencies:
            print("  [FX] No currencies found in BC")
            return

        # Fetch latest rate for each currency
        rates = {}
        latest_date = ""

        for currency in currencies:
            rate, date = _fetch_latest_rate(currency)
            if rate:
                rates[currency] = rate
                if not latest_date or date > latest_date:
                    latest_date = date

        if rates:
            _rate_cache["rates"]      = rates
            _rate_cache["fetched_at"] = time.time()
            _rate_cache["as_of_date"] = latest_date

            print(
                f"  [FX] Rates loaded from BC: "
                f"{len(rates)} currencies. "
                f"As of: {latest_date}"
            )
            for code, rate in sorted(rates.items()):
                print(f"    1 {code} = {rate} {LOCAL_CURRENCY}")

    except Exception as e:
        print(f"  [FX] Error fetching rates: {e}")


def _fetch_latest_rate(currency_code):
    """
    Fetches the most recent rate for a specific currency.
    Returns (rate, date) tuple or (None, None).
    """

    try:
        r = requests.get(
            BASE_URL,
            headers=get_headers(),
            params={
                "$filter":  f"currencyCode eq '{currency_code}'",
                "$orderby": "startingDate desc",
                "$top":     1,
                "$select":  (
                    "currencyCode,startingDate,"
                    "exchangeRateAmount,"
                    "relationalExchangeRateAmount"
                )
            },
            timeout=15
        )

        if r.ok:
            records = r.json().get("value", [])
            if records:
                record = records[0]
                base   = float(record.get("exchangeRateAmount", 1))
                rate   = float(
                    record.get("relationalExchangeRateAmount", 0)
                )
                date   = record.get("startingDate", "")

                if base > 0 and rate > 0:
                    # Normalise: rate per 1 unit of foreign currency
                    return round(rate / base, 4), date

    except Exception as e:
        print(f"  [FX] Error for {currency_code}: {e}")

    return None, None


def clear_cache():
    """Clears the rate cache — forces refresh on next call."""
    _rate_cache["rates"]      = {}
    _rate_cache["fetched_at"] = 0
    _rate_cache["as_of_date"] = ""
    print("  [FX] Rate cache cleared.")


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("BC EXCHANGE RATES TEST")
    print("=" * 60)

    # Load all rates
    _fetch_all_rates()

    info = get_rate_info()
    print(f"\nRates as of: {info['as_of']}")
    print(f"Source     : {info['source']}")
    print(f"Cache age  : {info['age_hours']}h")

    print("\n" + "=" * 60)
    print("CONVERSION TESTS")
    print("=" * 60)

    test_cases = [
        (89.95,  "USD", "INR", "Criminal Investigation"),
        (112.00, "GBP", "INR", "Concepts in International Relations"),
        (42.99,  "GBP", "INR", "Criminology: The Essentials"),
        (235.00, "USD", "INR", "Research Design"),
        (725.00, "INR", "INR", "An Intro to Qualitative Research"),
    ]

    for amount, from_cur, to_cur, title in test_cases:
        converted = convert(amount, from_cur, to_cur)
        rate      = get_rate(from_cur)
        print(
            f"\n  {title[:40]}"
            f"\n  {from_cur} {amount:,.2f} → "
            f"{to_cur} {converted:,.2f}"
            f"  (rate: 1 {from_cur} = {rate} {to_cur})"
        )

    print("\n" + "=" * 60)
    print("Testing cache — second call should use cache:")
    print("=" * 60)
    rate = get_rate("USD")
    print(f"USD rate: {rate}")
    rate2 = get_rate("USD")
    print(f"USD rate (cached): {rate2}")