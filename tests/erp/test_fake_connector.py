import pytest

from app.erp.connectors.fake import FakeERPConnector
from app.erp.exceptions import ERPNotFoundError


@pytest.fixture
def connector() -> FakeERPConnector:
    return FakeERPConnector()


# =============================================================================
# Customers
# =============================================================================


@pytest.mark.asyncio
async def test_get_customer_returns_seeded_customer(connector):
    customer = await connector.customers.get_customer("cust-1")

    assert customer.id == "cust-1"
    assert customer.name == "Acme Corp"


@pytest.mark.asyncio
async def test_get_customer_not_found_raises(connector):
    with pytest.raises(ERPNotFoundError):
        await connector.customers.get_customer("does-not-exist")


@pytest.mark.asyncio
async def test_search_customers_matches_name(connector):
    results = await connector.customers.search_customers("globex")

    assert len(results) == 1
    assert results[0].id == "cust-2"


@pytest.mark.asyncio
async def test_search_customers_no_match_returns_empty(connector):
    results = await connector.customers.search_customers("nonexistent")

    assert results == []


# =============================================================================
# Orders
# =============================================================================


@pytest.mark.asyncio
async def test_get_order_returns_seeded_order(connector):
    order = await connector.orders.get_order("order-1")

    assert order.id == "order-1"
    assert order.customer_id == "cust-1"


@pytest.mark.asyncio
async def test_get_order_not_found_raises(connector):
    with pytest.raises(ERPNotFoundError):
        await connector.orders.get_order("does-not-exist")


@pytest.mark.asyncio
async def test_search_orders_matches_customer(connector):
    results = await connector.orders.search_orders("cust-2")

    assert len(results) == 1
    assert results[0].id == "order-2"


# =============================================================================
# Inventory
# =============================================================================


@pytest.mark.asyncio
async def test_get_stock_returns_seeded_item(connector):
    stock = await connector.inventory.get_stock("prod-1")

    assert stock.product_id == "prod-1"
    assert stock.quantity_available == 90


@pytest.mark.asyncio
async def test_get_stock_not_found_raises(connector):
    with pytest.raises(ERPNotFoundError):
        await connector.inventory.get_stock("does-not-exist")


@pytest.mark.asyncio
async def test_search_products_matches_sku(connector):
    results = await connector.inventory.search_products("WIDGET")

    assert len(results) == 1
    assert results[0].id == "prod-1"


@pytest.mark.asyncio
async def test_check_availability_true_when_sufficient_stock(connector):
    available = await connector.inventory.check_availability("prod-1", 50)

    assert available is True


@pytest.mark.asyncio
async def test_check_availability_false_when_insufficient_stock(connector):
    available = await connector.inventory.check_availability("prod-1", 1000)

    assert available is False


@pytest.mark.asyncio
async def test_check_availability_not_found_raises(connector):
    with pytest.raises(ERPNotFoundError):
        await connector.inventory.check_availability("does-not-exist", 1)


# =============================================================================
# Invoices
# =============================================================================


@pytest.mark.asyncio
async def test_get_invoice_returns_seeded_invoice(connector):
    invoice = await connector.invoices.get_invoice("inv-1")

    assert invoice.id == "inv-1"
    assert invoice.customer_id == "cust-1"


@pytest.mark.asyncio
async def test_get_invoice_not_found_raises(connector):
    with pytest.raises(ERPNotFoundError):
        await connector.invoices.get_invoice("does-not-exist")


@pytest.mark.asyncio
async def test_search_invoices_matches_order(connector):
    results = await connector.invoices.search_invoices("order-2")

    assert len(results) == 1
    assert results[0].id == "inv-2"
