"""
bc_errors.py
============
Custom error types for the Business Central integration layer.

All BC errors are caught inside bc_client.py and converted
to safe return values (None / empty lists) so the rest of
the pipeline never sees an unhandled exception from this layer.
"""

import time


# =============================================================
# Custom Exception Types
# =============================================================

class BCError(Exception):
    """
    Base class for all Business Central errors.
    """
    pass


class BCAuthError(BCError):
    """
    Raised when authentication fails.

    Causes:
      - Invalid Client ID or Secret
      - Expired Client Secret
      - Admin consent not granted
      - Wrong Tenant ID
    """
    pass


class BCNotFoundError(BCError):
    """
    Raised when a requested resource does not exist in BC.

    Causes:
      - Customer not in BC
      - Product / Item not in BC
      - Company not found
    """
    pass


class BCNetworkError(BCError):
    """
    Raised when the BC API cannot be reached.

    Causes:
      - No internet connection
      - BC service temporarily unavailable
      - Firewall blocking the request
      - Request timeout
    """
    pass


class BCRateLimitError(BCError):
    """
    Raised when BC API returns HTTP 429 Too Many Requests.
    Handled with exponential backoff retry in retry_with_backoff().
    """
    pass


class BCAPIError(BCError):
    """
    Raised for unexpected BC API errors (HTTP 500, malformed response).

    Causes:
      - BC service internal error
      - Unexpected response format
      - Missing expected fields in response
    """
    pass


# =============================================================
# Retry Logic
# =============================================================

def retry_with_backoff(fn, max_attempts=3, base_delay=2):
    """
    Calls fn() up to max_attempts times with exponential backoff.

    Retries on:
      - BCRateLimitError (HTTP 429)
      - BCNetworkError   (timeout, connection error)

    Does NOT retry on:
      - BCAuthError      (wrong credentials — retrying won't help)
      - BCNotFoundError  (record missing — retrying won't help)
      - BCAPIError       (unexpected error — retrying unlikely to help)

    Backoff delays: 2s → 4s → 8s (base_delay ** attempt)

    If all attempts are exhausted, the last exception is re-raised
    and caught by bc_client.py which returns a safe None value.
    """

    last_exception = None

    for attempt in range(1, max_attempts + 1):

        try:
            return fn()

        except (BCRateLimitError, BCNetworkError) as e:

            last_exception = e
            delay = base_delay ** attempt

            print(
                f"  [BC] Attempt {attempt}/{max_attempts} failed: "
                f"{type(e).__name__}. "
                f"Retrying in {delay}s..."
            )

            time.sleep(delay)

        except (BCAuthError, BCNotFoundError, BCAPIError):
            # Non-retriable — raise immediately
            raise

    # All retries exhausted
    raise last_exception
