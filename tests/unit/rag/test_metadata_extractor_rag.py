from rules.models import DocumentType
from app.rag.chunker import MetadataExtractor


def test_extract_no_match(monkeypatch):
    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda text, filename: None,
    )

    class DummyField:
        def __init__(self):
            self.name = "invoice"
            self.patterns = [r"Invoice:\s*(\d+)"]

    result = MetadataExtractor.extract(
        "Nothing here",
        "doc.pdf",
    )

    assert "invoice" not in result


def test_extract_pattern_without_group(monkeypatch):
    monkeypatch.setattr(
        "app.ingestion.metadata_extractor.detect_document_type",
        lambda text, filename: None,
    )

    class DummyField:
        def __init__(self):
            self.name = "approved"
            self.patterns = [
                r"APPROVED",
            ]

    monkeypatch.setattr(
        "app.ingestion.metadata_extractor.FIELD_DEFINITIONS",
        {
            "approved": DummyField(),
        },
    )

    result = MetadataExtractor.extract(
        "Status: APPROVED",
        "doc.pdf",
    )

    assert result["approved"] == "APPROVED"


def test_extract_first_matching_pattern(monkeypatch):
    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda text, filename: None,
    )

    class DummyField:
        def __init__(self):
            self.name = "contract_number"
            self.patterns = [
                r"Contract:\s*(\d+)",
                r"Agreement:\s*(\d+)",
            ]

    result = MetadataExtractor.extract(
        "Agreement: 999\nContract: 123",
        "contract.pdf",
    )

    assert result["contract_number"] == "123"

def test_extract_fields(monkeypatch):
    monkeypatch.setattr(
        "app.ingestion.metadata_extractor.detect_document_type",
        lambda text, filename: None,
    )

    class DummyField:
        def __init__(self):
            self.name = "invoice_number"
            self.patterns = [r"Invoice:\s*(\d+)"]

    monkeypatch.setattr(
        "app.ingestion.metadata_extractor.FIELD_DEFINITIONS",
        {
            "invoice": DummyField(),
        },
    )

    result = MetadataExtractor.extract(
        text="Invoice: 12345",
        filename="invoice.pdf",
    )

    assert result["invoice_number"] == "12345"


def test_extract_document_type(monkeypatch):
    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda text, filename: "invoice",
    )

    result = MetadataExtractor.extract(
        text="Invoice #123",
        filename="invoice.pdf",
    )

    assert result["document_type"] == DocumentType.INVOICE


def test_extract_document_name_only(monkeypatch):
    monkeypatch.setattr(
        "app.ingestion.metadata_extractor.detect_document_type",
        lambda text, filename: None,
    )

    result = MetadataExtractor.extract(
        text="random text",
        filename="invoice.pdf",
    )

    assert result == {
        "document_name": "invoice.pdf",
    }
