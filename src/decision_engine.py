"""
decision_engine.py
==================
Routes emails to the correct workflow action.

Intents and their routing:

  Book workflows (AUTO_PROCESS or HUMAN_INTERVENTION):
    Quote Request
    Purchase Order
    Availability Check
    Pricing Clarification

  Journal workflow (ROUTE_JOURNALS):
    Journal Subscription
    Subscription Renewal

  Finance workflow (ROUTE_FINANCE):
    Invoice Query

  Support workflow (ROUTE_SUPPORT):
    Support Request

  Archive:
    Other
"""

from config import CONFIDENCE_THRESHOLD

BOOK_QUOTE_INTENTS = [
    "Quote Request",
    "Purchase Order",
    "Pricing Clarification",
]

AVAILABILITY_INTENTS = [
    "Availability Check",
]

JOURNAL_INTENTS = [
    "Journal Subscription",
    "Subscription Renewal",
]


def evaluate(
    intent,
    confidence,
    customer_found,
    missing_products,
    missing_information,
    validated_products=None
):

    # -----------------------------
    # Journal Workflow
    # Separate team handles these
    # -----------------------------

    if intent in JOURNAL_INTENTS:
        return {
            "action": "ROUTE_JOURNALS",
            "reason": (
                "Journal subscription or renewal request — "
                "routing to journals team"
            )
        }

    # -----------------------------
    # Support Workflow
    # -----------------------------

    if intent == "Support Request":
        return {
            "action": "ROUTE_SUPPORT",
            "reason": "Support request"
        }

    # -----------------------------
    # Finance Workflow
    # -----------------------------

    if intent == "Invoice Query":
        return {
            "action": "ROUTE_FINANCE",
            "reason": "Invoice query"
        }

    # -----------------------------
    # Archive
    # -----------------------------

    if intent == "Other":
        return {
            "action": "ARCHIVE",
            "reason": "No business action required"
        }

    # -----------------------------
    # Availability Check Workflow
    # Customer asking if book exists/is in stock
    # No quantity required — just confirm availability
    # -----------------------------

    if intent in AVAILABILITY_INTENTS:

        if not customer_found:
            return {
                "action": "HUMAN_INTERVENTION",
                "reason": "Customer not found in BC"
            }

        validated_count = (
            len(validated_products) if validated_products else 0
        )

        if validated_count > 0:
            return {
                "action": "AUTO_AVAILABILITY",
                "reason": (
                    f"{validated_count} title(s) confirmed available in BC"
                )
            }

        return {
            "action": "HUMAN_INTERVENTION",
            "reason": "Requested title(s) not found in BC catalogue"
        }

    # -----------------------------
    # Book Quote Workflow
    # -----------------------------

    if intent in BOOK_QUOTE_INTENTS:

        if confidence < CONFIDENCE_THRESHOLD:
            return {
                "action": "HUMAN_INTERVENTION",
                "reason": "Low AI confidence"
            }

        if not customer_found:
            return {
                "action": "HUMAN_INTERVENTION",
                "reason": "Customer not found"
            }

        # Filter out quantity from missing info check
        # Quantity defaults to 1 in classifier if not explicit
        real_missing = [
            m for m in missing_information
            if m.lower() != "quantity"
        ]

        if len(real_missing) > 0:
            return {
                "action": "HUMAN_INTERVENTION",
                "reason": f"Missing: {', '.join(real_missing)}"
            }

        validated_count = (
            len(validated_products) if validated_products else 0
        )

        # All products found
        if len(missing_products) == 0:
            return {
                "action": "AUTO_PROCESS",
                "reason": "Ready to generate quote"
            }

        # Some products found — partial quote
        if validated_count > 0:
            missing_titles = ", ".join(missing_products)
            return {
                "action": "AUTO_PROCESS_PARTIAL",
                "reason": (
                    f"Partial match — {validated_count} product(s) found, "
                    f"{len(missing_products)} not found in BC: "
                    f"{missing_titles}"
                ),
                "missing_products": missing_products
            }

        # No products found at all
        return {
            "action": "HUMAN_INTERVENTION",
            "reason": "No products found in BC"
        }

    # -----------------------------
    # Unknown Intent
    # -----------------------------

    return {
        "action": "HUMAN_INTERVENTION",
        "reason": f"Unrecognised intent: {intent}"
    }