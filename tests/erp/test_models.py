from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

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


def test_customer_valid():
    customer = Customer(id="cust-1", name="Acme Corp", email="billing@acme.example")

    assert customer.id == "cust-1"
    assert customer.is_active is True


def test_customer_requires_name():
    with pytest.raises(ValidationError):
        Customer(id="cust-1")


def test_product_valid():
    product = Product(
        id="prod-1",
        sku="WIDGET-001",
        name="Standard Widget",
        unit_price=Decimal("19.99"),
    )

    assert product.currency == "USD"
    assert product.unit_price == Decimal("19.99")


def test_product_requires_unit_price():
    with pytest.raises(ValidationError):
        Product(id="prod-1", sku="WIDGET-001", name="Standard Widget")


def test_inventory_item_quantity_available():
    item = InventoryItem(
        product_id="prod-1",
        sku="WIDGET-001",
        quantity_on_hand=Decimal("100"),
        quantity_reserved=Decimal("10"),
    )

    assert item.quantity_available == Decimal("90")


def test_order_valid():
    order = Order(
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
    )

    assert len(order.items) == 1
    assert order.status == OrderStatus.CONFIRMED


def test_order_requires_total_amount():
    with pytest.raises(ValidationError):
        Order(
            id="order-1",
            customer_id="cust-1",
            status=OrderStatus.DRAFT,
            created_at=datetime(2026, 1, 10, tzinfo=UTC),
        )


def test_invoice_valid():
    invoice = Invoice(
        id="inv-1",
        customer_id="cust-1",
        order_id="order-1",
        status=InvoiceStatus.PAID,
        total_amount=Decimal("39.98"),
        amount_due=Decimal("0"),
        issued_at=datetime(2026, 1, 11, tzinfo=UTC),
    )

    assert invoice.status == InvoiceStatus.PAID
    assert invoice.amount_due == Decimal("0")


def test_invoice_requires_issued_at():
    with pytest.raises(ValidationError):
        Invoice(
            id="inv-1",
            customer_id="cust-1",
            status=InvoiceStatus.DRAFT,
            total_amount=Decimal("10"),
            amount_due=Decimal("10"),
        )
