import json

from llm_client import ask_llm


def classify_email(messages):
    """
    Returns structured JSON extracted from the email.
    """

    response_text = ask_llm(
        messages,
        temperature=0
    )

    return json.loads(response_text)