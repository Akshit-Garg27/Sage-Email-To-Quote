"""
bc_auth.py
==========
OAuth2 Client Credentials token acquisition for Business Central.

Responsible for:
  - Requesting access tokens from Azure AD
  - Caching tokens until expiry
  - Raising BCAuthError on authentication failure

Single responsibility: provide a valid BC access token.
All other BC modules call get_bc_token() — they never
touch OAuth directly.
"""

import requests
from config import BC_CLIENT_ID, BC_CLIENT_SECRET, BC_TENANT_ID
from bc_errors import BCAuthError, BCNetworkError
from bc_cache import get_token, set_token


# =============================================================
# Token Endpoint
# =============================================================

BC_SCOPE = "https://api.businesscentral.dynamics.com/.default"

def _token_url():
    return (
        f"https://login.microsoftonline.com/"
        f"{BC_TENANT_ID}/oauth2/v2.0/token"
    )


# =============================================================
# Public Interface
# =============================================================

def get_bc_token():
    """
    Returns a valid BC access token.

    Checks cache first — if a valid cached token exists,
    returns it without making an API call.

    If no valid cached token exists, requests a new one
    from Azure AD using Client Credentials flow.

    Raises:
      BCAuthError    — invalid credentials, no consent, wrong tenant
      BCNetworkError — cannot reach Azure AD token endpoint
    """

    # Check cache first
    cached = get_token()

    if cached:
        print("  [BC Auth] Using cached token.")
        return cached

    # Request new token
    print("  [BC Auth] Requesting new token from Azure AD...")

    return _request_new_token()


def _request_new_token():
    """
    Requests a new OAuth2 token using Client Credentials flow.

    This is a machine-to-machine flow — no user login required.
    The app authenticates as itself using Client ID + Secret.
    """

    if not BC_CLIENT_ID:
        raise BCAuthError(
            "BC_CLIENT_ID not set in .env. "
            "Add your Azure App Registration Client ID."
        )

    if not BC_CLIENT_SECRET:
        raise BCAuthError(
            "BC_CLIENT_SECRET not set in .env. "
            "Generate a Client Secret in Azure App Registration."
        )

    if not BC_TENANT_ID:
        raise BCAuthError(
            "BC_TENANT_ID not set in .env. "
            "Add your BC Azure Tenant ID."
        )

    payload = {
        "grant_type": "client_credentials",
        "client_id": BC_CLIENT_ID,
        "client_secret": BC_CLIENT_SECRET,
        "scope": BC_SCOPE
    }

    try:
        response = requests.post(
            _token_url(),
            data=payload,
            timeout=30
        )

    except requests.exceptions.Timeout:
        raise BCNetworkError(
            "Token request timed out. "
            "Check network connectivity to login.microsoftonline.com"
        )

    except requests.exceptions.ConnectionError:
        raise BCNetworkError(
            "Cannot connect to Azure AD. "
            "Check network connectivity."
        )

    # Handle auth errors
    if response.status_code == 400:
        error = response.json().get("error", "unknown")
        description = response.json().get("error_description", "")
        raise BCAuthError(
            f"Authentication failed: {error}. {description}"
        )

    if response.status_code == 401:
        raise BCAuthError(
            "Unauthorized. Check Client ID and Client Secret."
        )

    if not response.ok:
        raise BCAuthError(
            f"Token request failed. "
            f"HTTP {response.status_code}: {response.text}"
        )

    data = response.json()

    token = data.get("access_token")
    expires_in = data.get("expires_in", 3600)

    if not token:
        raise BCAuthError(
            "Token response did not contain access_token. "
            f"Response: {data}"
        )

    # Cache the token
    set_token(token, expires_in)

    print("  [BC Auth] New token acquired successfully.")

    return token


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("BC AUTH — TOKEN TEST")
    print("=" * 60)

    try:

        token = get_bc_token()

        print(f"\n  Token acquired successfully.")
        print(f"  First 40 chars: {token[:40]}...")

        print("\n  Testing cache — requesting token again...")
        token2 = get_bc_token()

        if token == token2:
            print("  Cache working correctly — same token returned.")

        print("\n  Result: PASS")

    except Exception as e:
        print(f"\n  Result: FAIL")
        print(f"  Error : {type(e).__name__}: {e}")
