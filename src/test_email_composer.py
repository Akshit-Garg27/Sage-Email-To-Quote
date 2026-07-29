from file_loader import load_prompt
from outlook_com import (
    get_unread_emails,
    save_attachments
)
from document_reader import read_document
from classifier import classify_email
from mock_bc import (
    get_customer,
    validate_products
)
from quote_generator import generate_quote
from email_composer import compose_email


# ---------------------------------------
# Load Classifier Prompt
# ---------------------------------------

system_prompt = load_prompt()

# ---------------------------------------
# Read Latest Email
# ---------------------------------------

emails = get_unread_emails(limit=1)

if not emails:

    print("No unread emails found.")
    exit()

email = emails[0]

# ---------------------------------------
# Save Attachments
# ---------------------------------------

saved_files = save_attachments(
    email["mail_item"]
)

attachment_text = ""

for file in saved_files:

    print(f"Reading: {file}")

    attachment_text += read_document(file)
    attachment_text += "\n\n"

# ---------------------------------------
# Build SAME prompt as email_processor.py
# ---------------------------------------

messages = [

    {
        "role": "system",
        "content": system_prompt
    },

    {
        "role": "user",
        "content": f"""
EMAIL SUBJECT

{email['subject']}

--------------------------------

EMAIL BODY

{email['body']}

--------------------------------

ATTACHMENT CONTENT

{attachment_text}
"""
    }

]

# ---------------------------------------
# Classify Email
# ---------------------------------------

result = classify_email(messages)

print("\n========== CLASSIFIER OUTPUT ==========")
print(result)

print("\nOrganization Extracted:")
print(repr(result["organization"]))

# ---------------------------------------
# Customer Lookup
# ---------------------------------------

customer = get_customer(
    result["organization"].strip()
)

print("\nCustomer Lookup Result:")
print(customer)

if customer is None:

    print("\nCustomer NOT FOUND.")
    exit()

# ---------------------------------------
# Product Validation
# ---------------------------------------

validated_products, missing_products = validate_products(
    result["products"]
)

print("\nValidated Products:")
print(validated_products)

print("\nMissing Products:")
print(missing_products)

# ---------------------------------------
# Generate Quote
# ---------------------------------------

quote = generate_quote(
    result,
    customer,
    validated_products,
    email
)

print("\nQuote Generated Successfully.")

# ---------------------------------------
# Compose Email
# ---------------------------------------

generated_email = compose_email(
    quote,
    email
)

print("\n================ GENERATED EMAIL ================\n")

print(generated_email)