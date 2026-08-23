"""
ERPConnector abstraction.

Application code should depend on this type alone. Concrete connectors
(a future OdooConnector, a FakeERPConnector for tests, or connectors for
other ERP systems later) provide the four services below without the
caller needing to know which vendor is behind them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.erp.interfaces import (
    CustomerService,
    InventoryService,
    InvoiceService,
    OrderService,
)


class ERPConnector(ABC):
    """Aggregates the ERP service interfaces behind a single dependency."""

    @property
    @abstractmethod
    def customers(self) -> CustomerService: ...

    @property
    @abstractmethod
    def orders(self) -> OrderService: ...

    @property
    @abstractmethod
    def inventory(self) -> InventoryService: ...

    @property
    @abstractmethod
    def invoices(self) -> InvoiceService: ...
