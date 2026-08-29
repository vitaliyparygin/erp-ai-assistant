"""
ERP connector dependency injection.

Follows the same Annotated[X, Depends(get_x)] pattern used in
app/core/dependencies.py. Nothing here attempts to connect to a real ERP
system: the default implementation is the in-memory FakeERPConnector, so
application startup and tests never require a live ERP server.

When a real connector (e.g. OdooConnector) is implemented in a later
roadmap phase, swap the return of get_erp_connector accordingly (likely
selected via settings) — callers depending on ERPConnectorDep do not need
to change.
"""

from typing import Annotated

from fastapi import Depends

from app.erp.connector import ERPConnector
from app.erp.connectors.fake import FakeERPConnector

# A single in-memory instance is reused across requests: it holds no
# per-request state beyond its static seed data, and avoids handing every
# request a fresh (identical) copy of the fake dataset.
_fake_connector = FakeERPConnector()


async def get_erp_connector() -> ERPConnector:
    """Provide the active ERPConnector implementation.

    Currently always returns FakeERPConnector. A future phase will select
    a real connector (e.g. OdooConnector) based on settings, without
    changing this function's signature or ERPConnectorDep's usage sites.
    """
    return _fake_connector


ERPConnectorDep = Annotated[ERPConnector, Depends(get_erp_connector)]
