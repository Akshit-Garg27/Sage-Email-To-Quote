from file_loader import load_prompt
from llm_client import ask_llm


def compose_email(quote, original_email):

    system_prompt = load_prompt("email_composer_prompt.txt")

    user_prompt = f"""
Customer Information

Organization:
{quote['customer']['organization']}

Contact Person:
{quote['customer']['contact_person']}

Customer Email:
{quote['customer']['email']}

Country:
{quote['customer']['country']}

Currency:
{quote['customer']['currency']}

----------------------------------------

Original Subject

{original_email['subject']}

----------------------------------------

Original Email

{original_email['body']}

----------------------------------------

Quote Number:
{quote['quote_number']}

Quote Date:
{quote['date']}

Valid Until:
{quote['expiry_date']}

----------------------------------------

Products
"""

    for item in quote["items"]:

        user_prompt += f"""

- {item['description']}
  Quantity: {item['quantity']}
"""

    user_prompt += f"""

----------------------------------------

Grand Total

{quote['pricing']['grand_total']} {quote['customer']['currency']}

----------------------------------------

Write a professional reply.

Return ONLY the email body.
"""

    messages = [

        {
            "role": "system",
            "content": system_prompt
        },

        {
            "role": "user",
            "content": user_prompt
        }

    ]

    return ask_llm(
        messages,
        temperature=0.4
    )