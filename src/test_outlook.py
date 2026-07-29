from outlook_reader import get_latest_email

email = get_latest_email()

if email is None:
    print("No emails found.")
else:
    print("\n===== LATEST EMAIL =====")
    print(f"Subject : {email['subject']}")
    print(f"From    : {email['from']}")
    print(f"Received: {email['received']}")
    print("\nBody:\n")
    print(email["body"])