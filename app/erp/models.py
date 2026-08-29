"""
ERP-independent domain models.

These represent common business concepts (customers, orders, inventory,
invoices) and must not encode any vendor-specific structure (e.g. Odoo's
res.partner / sale.order / account.move naming or fields). Any ERP connector
implementation is responsible for translating its own vendor records into
these models.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import Field, computed_field

from app.models.schemas import DomainModel

# =============================================================================
# Enums
# =============================================================================


class OrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


# =============================================================================
# Customer
# =============================================================================


class Customer(DomainModel):
    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Product / Inventory
# =============================================================================


class Product(DomainModel):
    id: str
    sku: str
    name: str
    description: str | None = None
    unit_price: Decimal
    currency: str = "USD"
    is_active: bool = True


class InventoryItem(DomainModel):
    product_id: str
    sku: str
    quantity_on_hand: Decimal
    quantity_reserved: Decimal = Decimal("0")
    warehouse_id: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def quantity_available(self) -> Decimal:
        return self.quantity_on_hand - self.quantity_reserved


# =============================================================================
# Order
# =============================================================================


class OrderItem(DomainModel):
    product_id: str
    sku: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class Order(DomainModel):
    id: str
    customer_id: str
    status: OrderStatus
    items: list[OrderItem] = Field(default_factory=list)
    total_amount: Decimal
    currency: str = "USD"
    created_at: datetime
    updated_at: datetime | None = None


# =============================================================================
# Invoice
# =============================================================================


class Invoice(DomainModel):
    id: str
    customer_id: str
    order_id: str | None = None
    status: InvoiceStatus
    total_amount: Decimal
    amount_due: Decimal
    currency: str = "USD"
    issued_at: datetime
    due_at: datetime | None = None
