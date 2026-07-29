from config import client, MODEL_NAME


def ask_llm(messages, temperature=0):
    """
    Sends messages to the LLM and returns the raw text response.
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature
    )

    return response.choices[0].message.content