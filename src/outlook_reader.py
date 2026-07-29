import requests
import msal

from config import CLIENT_ID, TENANT_ID

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = [
    "User.Read",
    "Mail.Read"
]


def get_access_token():

    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY
    )

    # Try to use an existing signed-in account first
    accounts = app.get_accounts()

    if accounts:
        result = app.acquire_token_silent(
            SCOPES,
            account=accounts[0]
        )

        if result and "access_token" in result:
            return result["access_token"]

    # Interactive login
    result = app.acquire_token_interactive(
        scopes=SCOPES
    )

    if "access_token" in result:
        return result["access_token"]

    # Show the full error if authentication fails
    raise Exception(result)


def get_latest_email():

    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = (
        "https://graph.microsoft.com/v1.0/me/messages"
        "?$orderby=receivedDateTime desc"
        "&$top=1"
    )

    response = requests.get(
        url,
        headers=headers
    )

    response.raise_for_status()

    messages = response.json()["value"]

    if not messages:
        return None

    message = messages[0]

    return {
        "subject": message["subject"],
        "from": message["from"]["emailAddress"]["address"],
        "received": message["receivedDateTime"],
        "body": message["body"]["content"]
    }