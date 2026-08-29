"""
In-memory ERPConnector implementation for tests and local development.

Satisfies the same interfaces a real connector (e.g. a future
OdooConnector) would, using a small set of deterministic seed data, so
callers never need to reach a real ERP system in tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.erp.connector import ERPConnector
from app.erp.exceptions import ERPNotFoundError
from app.erp.interfaces import (
    CustomerService,
    InventoryService,
    InvoiceService,
    OrderService,
)
from app.erp.models import (
    Customer,
    InventoryItem,
    Invoice,
    InvoiceStatus,
    Order,
    OrderItem,
    OrderStatus,
    Product,
)

# =============================================================================
# Seed data
# =============================================================================

_CUSTOMERS: dict[str, Customer] = {
    "cust-1": Customer(
        id="cust-1",
        name="Acme Corp",
        email="billing@acme.example",
        phone="+1-555-0100",
    ),
    "cust-2": Customer(
        id="cust-2",
        name="Globex LLC",
        email="ap@globex.example",
        phone="+1-555-0200",
    ),
}

_PRODUCTS: dict[str, Product] = {
    "prod-1": Product(
        id="prod-1",
        sku="WIDGET-001",
        name="Standard Widget",
        description="A standard widget.",
        unit_price=Decimal("19.99"),
    ),
    "prod-2": Product(
        id="prod-2",
        sku="GADGET-002",
        name="Deluxe Gadget",
        description="A deluxe gadget.",
        unit_price=Decimal("49.50"),
    ),
}

_INVENTORY: dict[str, InventoryItem] = {
    "prod-1": InventoryItem(
        product_id="prod-1",
        sku="WIDGET-001",
        quantity_on_hand=Decimal("100"),
        quantity_reserved=Decimal("10"),
        warehouse_id="wh-main",
    ),
    "prod-2": InventoryItem(
        product_id="prod-2",
        sku="GADGET-002",
        quantity_on_hand=Decimal("5"),
        quantity_reserved=Decimal("0"),
        warehouse_id="wh-main",
    ),
}

_ORDERS: dict[str, Order] = {
    "order-1": Order(
        id="order-1",
        customer_id="cust-1",
        status=OrderStatus.CONFIRMED,
        items=[
            OrderItem(
                product_id="prod-1",
                sku="WIDGET-001",
                quantity=Decimal("2"),
                unit_price=Decimal("19.99"),
                subtotal=Decimal("39.98"),
            )
        ],
        total_amount=Decimal("39.98"),
        created_at=datetime(2026, 1, 10, tzinfo=UTC),
    ),
    "order-2": Order(
        id="order-2",
        customer_id="cust-2",
        status=OrderStatus.SHIPPED,
        items=[
            OrderItem(
                product_id="prod-2",
                sku="GADGET-002",
                quantity=Decimal("1"),
                unit_price=Decimal("49.50"),
                subtotal=Decimal("49.50"),
            )
        ],
        total_amount=Decimal("49.50"),
        created_at=datetime(2026, 2, 5, tzinfo=UTC),
    ),
}

_INVOICES: dict[str, Invoice] = {
    "inv-1": Invoice(
        id="inv-1",
        customer_id="cust-1",
        order_id="order-1",
        status=InvoiceStatus.PAID,
        total_amount=Decimal("39.98"),
        amount_due=Decimal("0"),
        issued_at=datetime(2026, 1, 11, tzinfo=UTC),
    ),
    "inv-2": Invoice(
        id="inv-2",
        customer_id="cust-2",
        order_id="order-2",
        status=InvoiceStatus.OPEN,
        total_amount=Decimal("49.50"),
        amount_due=Decimal("49.50"),
        issued_at=datetime(2026, 2, 6, tzinfo=UTC),
    ),
}


# =============================================================================
# Service implementations
# =============================================================================


class FakeCustomerService(CustomerService):
    async def get_customer(self, customer_id: str) -> Customer:
        try:
            return _CUSTOMERS[customer_id]
        except KeyError:
            raise ERPNotFoundError(
                f"Customer '{customer_id}' not found",
                entity_type="Customer",
                entity_id=customer_id,
            ) from None

    async def search_customers(self, query: str) -> list[Customer]:
        q = query.lower()
        return [
            c
            for c in _CUSTOMERS.values()
            if q in c.name.lower() or (c.email and q in c.email.lower())
        ]


class FakeOrderService(OrderService):
    async def get_order(self, order_id: str) -> Order:
        try:
            return _ORDERS[order_id]
        except KeyError:
            raise ERPNotFoundError(
                f"Order '{order_id}' not found",
                entity_type="Order",
                entity_id=order_id,
            ) from None

    async def search_orders(self, query: str) -> list[Order]:
        q = query.lower()
        return [
            o
            for o in _ORDERS.values()
            if q in o.id.lower() or q in o.customer_id.lower() or q in o.status.lower()
        ]


class FakeInventoryService(InventoryService):
    async def get_stock(self, product_id: str) -> InventoryItem:
        try:
            return _INVENTORY[product_id]
        except KeyError:
            raise ERPNotFoundError(
                f"Inventory for product '{product_id}' not found",
                entity_type="InventoryItem",
                entity_id=product_id,
            ) from None

    async def search_products(self, query: str) -> list[Product]:
        q = query.lower()
        return [
            p for p in _PRODUCTS.values() if q in p.name.lower() or q in p.sku.lower()
        ]

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        stock = await self.get_stock(product_id)
        return stock.quantity_available >= Decimal(quantity)


class FakeInvoiceService(InvoiceService):
    async def get_invoice(self, invoice_id: str) -> Invoice:
        try:
            return _INVOICES[invoice_id]
        except KeyError:
            raise ERPNotFoundError(
                f"Invoice '{invoice_id}' not found",
                entity_type="Invoice",
                entity_id=invoice_id,
            ) from None

    async def search_invoices(self, query: str) -> list[Invoice]:
        q = query.lower()
        return [
            i
            for i in _INVOICES.values()
            if q in i.id.lower()
            or q in i.customer_id.lower()
            or (i.order_id is not None and q in i.order_id.lower())
            or q in i.status.lower()
        ]


class FakeERPConnector(ERPConnector):
    """Deterministic in-memory ERPConnector for tests and local development."""

    def __init__(self) -> None:
        self._customers = FakeCustomerService()
        self._orders = FakeOrderService()
        self._inventory = FakeInventoryService()
        self._invoices = FakeInvoiceService()

    @property
    def customers(self) -> CustomerService:
        return self._customers

    @property
    def orders(self) -> OrderService:
        return self._orders

    @property
    def inventory(self) -> InventoryService:
        return self._inventory

    @property
    def invoices(self) -> InvoiceService:
        return self._invoices
