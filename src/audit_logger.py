from datetime import datetime


def log_decision(result, decision, email=None):
    """
    Logs a decision to audit_log.txt.

    Args:
      result   : classifier output dict
      decision : decision string (e.g. "Quote Approved")
      email    : original email dict (optional, for ConversationID)
    """

    with open("audit_log.txt", "a", encoding="utf-8") as file:

        file.write(f"\n{'='*40}\n")
        file.write(f"Timestamp    : {datetime.now()}\n")
        file.write(f"Intent       : {result['intent']}\n")
        file.write(f"Confidence   : {result['confidence']}\n")
        file.write(f"Organization : {result.get('organization', '')}\n")
        file.write(f"Decision     : {decision}\n")

        # Store ConversationID for thread tracking
        if email and email.get("conversation_id"):
            file.write(
                f"ConversationID: {email['conversation_id']}\n"
            )