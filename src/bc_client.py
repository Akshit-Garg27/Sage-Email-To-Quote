"""
bc_client.py
============
Public Business Central integration interface.

This is the ONLY file that email_processor.py imports from.
It exposes exactly the same two functions as mock_bc.py:

  get_customer(organization)   → dict | None
  validate_products(products)  → (validated, missing)

Internally delegates to bc_customer.py and bc_items.py.

Switching between mock and live BC:
  BC_MODE=mock → email_processor.py imports from mock_bc
  BC_MODE=live → email_processor.py imports from bc_client

No other module in the pipeline needs to know this exists.
"""

from bc_customer import get_customer
from bc_items import validate_products

# Both functions are imported directly and re-exported.
# email_processor.py calls them identically to mock_bc.py.
# This file is intentionally minimal — it is a clean facade.

__all__ = ["get_customer", "validate_products"]
