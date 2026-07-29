import os
import win32com.client


# =============================================================
# Email Reading
# =============================================================

def get_unread_emails(limit=1):
    """
    Returns unread Outlook emails with ConversationID.
    """

    outlook   = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    inbox     = namespace.GetDefaultFolder(6)

    messages = inbox.Items
    messages.Sort("[ReceivedTime]", True)

    emails = []
    count  = 0

    for message in messages:

        if message.Class != 43:
            continue

        if not message.UnRead:
            continue

        try:
            sender = message.Sender.GetExchangeUser().PrimarySmtpAddress
            if sender is None:
                sender = message.SenderEmailAddress
        except Exception:
            sender = message.SenderEmailAddress

        attachments = []
        for attachment in message.Attachments:
            attachments.append({
                "name": attachment.FileName,
                "size": attachment.Size
            })

        # Get ConversationID safely
        try:
            conv_id = message.ConversationID
        except Exception:
            conv_id = None

        emails.append({
            "subject":         message.Subject,
            "from":            sender,
            "received":        str(message.ReceivedTime),
            "body":            message.Body,
            "unread":          message.UnRead,
            "attachments":     attachments,
            "mail_item":       message,
            "conversation_id": conv_id
        })

        count += 1
        # limit=0 means no limit — process all unread emails
        if limit > 0 and count >= limit:
            break

    return emails


# =============================================================
# Thread Reading
# =============================================================

def get_thread_context(mail_item, inbox):
    """
    Reads all emails in the same conversation thread.

    Uses ConversationIndex prefix matching — the correct
    COM approach that avoids the Restrict() filter error.

    ConversationIndex structure:
      First 22 bytes = conversation root identifier
      Each reply appends 5 bytes
      Emails in the same thread share the same first 22 bytes

    Returns a structured thread summary string ready to
    inject into the LLM prompt, or empty string if:
      - No prior emails in thread
      - Thread reading fails for any reason

    Never raises — all errors handled gracefully.
    """

    try:
        # Get the conversation index prefix (first 22 bytes)
        # This identifies the root conversation
        conv_index = getattr(mail_item, "ConversationIndex", None)

        if not conv_index or len(conv_index) < 22:
            return ""

        # Prefix is the first 22 chars of the ConversationIndex
        # All emails in the same thread share this prefix
        prefix = conv_index[:22]

        thread_emails = []

        # Iterate all inbox items — no Restrict() needed
        # Check ConversationIndex prefix for each item
        for item in inbox.Items:

            try:
                if item.Class != 43:
                    continue

                item_index = getattr(item, "ConversationIndex", None)
                if not item_index:
                    continue

                # Skip the current email itself
                if item.EntryID == mail_item.EntryID:
                    continue

                # Check if same conversation
                if item_index[:22] != prefix:
                    continue

                try:
                    sender = (
                        item.Sender.GetExchangeUser().PrimarySmtpAddress
                        or item.SenderEmailAddress
                    )
                except Exception:
                    sender = item.SenderEmailAddress

                thread_emails.append({
                    "from":     sender,
                    "received": str(item.ReceivedTime),
                    "subject":  item.Subject,
                    "body":     item.Body or ""
                })

            except Exception:
                continue

        if not thread_emails:
            return ""

        # Sort oldest to newest
        thread_emails.sort(key=lambda x: x["received"])

        print(
            f"  [Thread] Found {len(thread_emails)} "
            f"previous email(s) in this conversation"
        )

        # Build thread context string
        return _build_thread_context(thread_emails)

    except Exception as e:
        # Graceful fallback — thread reading is optional
        print(f"  [Thread] Could not read thread history: {e}")
        return ""


def _build_thread_context(thread_emails):
    """
    Builds a concise thread summary from previous emails.

    Design decisions:
    - Shows all emails but truncates long bodies
    - Marks each email clearly with sender and date
    - Keeps the most recent email bodies in full
      (they are most relevant to current request)
    - Truncates older emails to first 500 chars
      to avoid overwhelming the LLM context

    The LLM is instructed to use this as background
    context and focus on the latest (primary) email.
    """

    lines = []
    lines.append("CONVERSATION HISTORY")
    lines.append("(Earlier emails — oldest first)")
    lines.append("=" * 50)

    total = len(thread_emails)

    for i, email in enumerate(thread_emails):

        lines.append(f"\nFrom    : {email['from']}")
        lines.append(f"Date    : {email['received'][:19]}")
        lines.append(f"Subject : {email['subject']}")
        lines.append("")

        body = (email["body"] or "").strip()

        # Keep last 2 emails in full — truncate older ones
        if i >= total - 2:
            lines.append(body[:2000])
        else:
            if len(body) > 500:
                lines.append(body[:500])
                lines.append(
                    f"... [{len(body) - 500} more characters]"
                )
            else:
                lines.append(body)

        lines.append("\n" + "—" * 50)

    return "\n".join(lines)


# =============================================================
# Mark as Read
# =============================================================

def mark_as_read(mail_item):
    """Marks an email as read."""
    mail_item.UnRead = False
    mail_item.Save()


# =============================================================
# Save Attachments
# =============================================================

def save_attachments(mail_item):
    """
    Saves all attachments from an Outlook email.
    Returns list of saved file paths.
    """

    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    attachments_root = os.path.join(project_root, "attachments")
    os.makedirs(attachments_root, exist_ok=True)

    folder_name = mail_item.ReceivedTime.strftime("%Y%m%d_%H%M%S")
    save_folder = os.path.join(attachments_root, folder_name)
    os.makedirs(save_folder, exist_ok=True)

    saved_files = []

    for attachment in mail_item.Attachments:
        file_path = os.path.join(save_folder, attachment.FileName)
        attachment.SaveAsFile(file_path)
        saved_files.append(file_path)

    return saved_files


# =============================================================
# Standalone Test
# =============================================================

if __name__ == "__main__":

    outlook   = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    inbox     = namespace.GetDefaultFolder(6)

    emails = get_unread_emails(limit=1)

    print(f"\nFound {len(emails)} unread email(s).\n")

    for email in emails:
        print(f"Subject : {email['subject']}")
        print(f"From    : {email['from']}")

        thread = get_thread_context(email["mail_item"], inbox)

        if thread:
            print(f"\nThread context found:")
            print(thread[:500])
        else:
            print("\nNo thread history (standalone email)")