"""
Lightweight architectural boundary check: the ERP domain/interfaces/
connector-abstraction modules must not import any ERP-vendor-specific
infrastructure (e.g. an Odoo client library, or `odoo` itself). Concrete
vendor connectors (added in a later phase) live under app/erp/connectors/
and are exempt — that's exactly where vendor-specific code belongs.
"""

import ast
from pathlib import Path

import app.erp.connector
import app.erp.exceptions
import app.erp.interfaces
import app.erp.models

VENDOR_MARKERS = ("odoo",)

CORE_MODULES = [
    app.erp.models,
    app.erp.interfaces,
    app.erp.connector,
    app.erp.exceptions,
]


def _imported_names(source: str) -> list[str]:
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_core_erp_modules_do_not_import_vendor_infrastructure():
    for module in CORE_MODULES:
        source = Path(module.__file__).read_text()
        imported = _imported_names(source)

        offending = [
            name
            for name in imported
            if any(marker in name.lower() for marker in VENDOR_MARKERS)
        ]

        assert (
            not offending
        ), f"{module.__name__} imports vendor-specific module(s): {offending}"


def test_fake_connector_satisfies_erp_connector_interface():
    from app.erp.connector import ERPConnector
    from app.erp.connectors.fake import FakeERPConnector

    assert issubclass(FakeERPConnector, ERPConnector)
