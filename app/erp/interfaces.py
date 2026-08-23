"""
ERP service interfaces.

Defined as ABCs with abstractmethod, matching the existing interface
convention used elsewhere in the codebase (see app/llm/protocol.py's
LLMProtocol). These are read-oriented for this phase; write operations
belong to a later roadmap phase.

Application code (future ERP tools / agents) should depend only on these
interfaces, never on a concrete connector such as an Odoo client.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.erp.models import Customer, InventoryItem, Invoice, Order, Product


class CustomerService(ABC):
    """Read access to ERP customer records."""

    @abstractmethod
    async def get_customer(self, customer_id: str) -> Customer:
        """Fetch a single customer by id. Raises ERPNotFoundError if missing."""
        raise NotImplementedError

    @abstractmethod
    async def search_customers(self, query: str) -> list[Customer]:
        """Search customers by name, email, or other identifying text."""
        raise NotImplementedError


class OrderService(ABC):
    """Read access to ERP sales orders."""

    @abstractmethod
    async def get_order(self, order_id: str) -> Order:
        """Fetch a single order by id. Raises ERPNotFoundError if missing."""
        raise NotImplementedError

    @abstractmethod
    async def search_orders(self, query: str) -> list[Order]:
        """Search orders by customer, reference, or other identifying text."""
        raise NotImplementedError


class InventoryService(ABC):
    """Read access to ERP product and stock information."""

    @abstractmethod
    async def get_stock(self, product_id: str) -> InventoryItem:
        """Fetch stock levels for a product. Raises ERPNotFoundError if missing."""
        raise NotImplementedError

    @abstractmethod
    async def search_products(self, query: str) -> list[Product]:
        """Search products by name, SKU, or other identifying text."""
        raise NotImplementedError

    @abstractmethod
    async def check_availability(self, product_id: str, quantity: int) -> bool:
        """Return True if at least `quantity` units are available."""
        raise NotImplementedError


class InvoiceService(ABC):
    """Read access to ERP invoices."""

    @abstractmethod
    async def get_invoice(self, invoice_id: str) -> Invoice:
        """Fetch a single invoice by id. Raises ERPNotFoundError if missing."""
        raise NotImplementedError

    @abstractmethod
    async def search_invoices(self, query: str) -> list[Invoice]:
        """Search invoices by customer, order, or other identifying text."""
        raise NotImplementedError
