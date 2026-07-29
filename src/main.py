import os
import traceback
import win32com.client

from file_loader import load_prompt
from outlook_com import get_unread_emails
from email_processor import process_email

# -----------------------------
# Load Prompt
# -----------------------------

system_prompt = load_prompt("classifier_prompt.txt")

# -----------------------------
# Connect to Outlook
# Get inbox reference for thread reading
# -----------------------------

outlook   = win32com.client.Dispatch("Outlook.Application")
namespace = outlook.GetNamespace("MAPI")
inbox     = namespace.GetDefaultFolder(6)

# -----------------------------
# Read All Unread Emails
# limit=0 means no limit — process everything
# -----------------------------

emails = get_unread_emails(limit=0)

if not emails:
    print("No unread emails found.")
    exit()

print(f"\nFound {len(emails)} unread email(s).\n")

# -----------------------------
# Create logs directory
# -----------------------------

os.makedirs("logs", exist_ok=True)

# -----------------------------
# Process Each Email
# One failure does not stop the rest
# -----------------------------

processed = 0
errors    = 0

for i, email in enumerate(emails, 1):

    print(f"\n[{i} of {len(emails)}]")

    try:

        process_email(
            email=email,
            system_prompt=system_prompt,
            inbox=inbox
        )

        processed += 1

    except Exception as e:

        errors += 1

        print(f"\n  ERROR processing email: {email['subject'][:60]}")
        print(f"  {e}")
        print(traceback.format_exc())
        print("  Continuing to next email...\n")

        continue

# -----------------------------
# Summary
# -----------------------------

print(f"\n{'='*40}")
print(f"Run complete: {processed} processed, {errors} error(s)")
print(f"{'='*40}\n")