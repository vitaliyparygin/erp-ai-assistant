import pytest
from unittest.mock import patch
from app.ingestion.metadata_extractor import MetadataExtractor
from rules.models import DocumentType


class TestMetadataExtractor:
    def test_returns_document_name(self):
        metadata = MetadataExtractor.extract(
            "Hello world",
            "sample.pdf",
        )

        assert metadata["document_name"] == "sample.pdf"

    def test_detects_invoice(self):
        metadata = MetadataExtractor.extract(
            "Invoice Number: INV-100",
            "invoice.pdf",
        )

        assert metadata["document_type"] == DocumentType.INVOICE

    def test_detects_contract(self):
        metadata = MetadataExtractor.extract(
            "Service Agreement\nContract Number: SC-100",
            "contract.pdf",
        )

        assert metadata["document_type"] == DocumentType.CONTRACT

    def test_detects_opportunity(self):
        metadata = MetadataExtractor.extract(
            "Opportunity\nERP Rollout",
            "crm.pdf",
        )

        assert metadata["document_type"] == DocumentType.CRM_OPPORTUNITY

    def test_unknown_document_type(self):
        metadata = MetadataExtractor.extract(
            "Hello world",
            "note.txt",
        )

        assert "document_type" not in metadata

    def test_extract_invoice_number(self):
        metadata = MetadataExtractor.extract(
            "Invoice Number: INV-1001",
            "invoice.pdf",
        )

        assert metadata["invoice_number"] == "INV-1001"

    def test_extract_customer(self):
        metadata = MetadataExtractor.extract(
            "Bill To: Acme Corp",
            "invoice.pdf",
        )

        assert metadata["customer"] == "Acme Corp"

    def test_extract_amount(self):
        metadata = MetadataExtractor.extract(
            "Total Due: $1,250.00",
            "invoice.pdf",
        )

        assert metadata["amount"] == "1,250.00"

    def test_extract_currency(self):
        metadata = MetadataExtractor.extract(
            "Currency: USD",
            "invoice.pdf",
        )

        assert metadata["currency"] == "USD"

    def test_extract_contract_number(self):
        metadata = MetadataExtractor.extract(
            "Contract Number: SC-2024-001",
            "contract.pdf",
        )

        assert metadata["contract_number"] == "SC-2024-001"

    def test_extract_contractor(self):
        metadata = MetadataExtractor.extract(
            "Contractor: ERP Solutions LLC",
            "contract.pdf",
        )

        assert metadata["contractor"] == "ERP Solutions LLC"

    def test_extract_signed_date(self):
        metadata = MetadataExtractor.extract(
            "Signed: 2024-01-15",
            "contract.pdf",
        )

        assert metadata["signed"] == "2024-01-15"

    def test_extract_valid_until(self):
        metadata = MetadataExtractor.extract(
            "Valid Until: 2025-01-15",
            "contract.pdf",
        )

        assert metadata["valid_until"] == "2025-01-15"

    def test_case_insensitive(self):
        metadata = MetadataExtractor.extract(
            "invoice number: inv-999",
            "invoice.pdf",
        )

        assert metadata["invoice_number"] == "inv-999"

    def test_multiple_patterns_first_match(self):
        text = """
        Invoice Number: INV-100
        
        Invoice Number: INV-200
        """

        metadata = MetadataExtractor.extract(text, "invoice.pdf")

        assert metadata["invoice_number"] == "INV-100"

    def test_missing_fields_are_not_added(self):
        metadata = MetadataExtractor.extract(
            DocumentType.INVOICE,
            "invoice.pdf",
        )

        assert "amount" not in metadata
        assert "customer" not in metadata
        assert "currency" not in metadata

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Invoice Number: INV-100", DocumentType.INVOICE),
            ("Service Agreement\nContract Number: C-001", DocumentType.CONTRACT),
            ("Opportunity Stage: Qualified", DocumentType.CRM_OPPORTUNITY),
            ("Договір", DocumentType.CONTRACT),
        ],
    )
    def test_document_type(self, text, expected):
        metadata = MetadataExtractor.extract(text, "doc.pdf")
        assert metadata["document_type"] == expected

    @pytest.mark.parametrize(
        ("text", "field", "value"),
        [
            ("Invoice Number: INV-1", "invoice_number", "INV-1"),
            ("Bill To: Acme", "customer", "Acme"),
            ("Total Due: $123.45", "amount", "123.45"),
            ("Currency: USD", "currency", "USD"),
        ],
    )
    def test_extract_fields(self, text, field, value):
        metadata = MetadataExtractor.extract(text, "doc.pdf")
        assert metadata[field] == value

    @patch("app.ingestion.metadata_extractor.detect_document_type")
    def test_calls_rules(self, mock_detect):
        mock_detect.return_value = DocumentType.INVOICE

        metadata = MetadataExtractor.extract(
            "Invoice Number: INV-1",
            "invoice.pdf",
        )

        mock_detect.assert_called_once()
        assert metadata["document_type"] == DocumentType.INVOICE

    @patch("app.ingestion.metadata_extractor.detect_document_type")
    def test_without_document_type(self, mock_detect):
        mock_detect.return_value = None

        metadata = MetadataExtractor.extract(
            "Some text",
            "doc.pdf",
        )

        assert "document_type" not in metadata

    @patch("app.ingestion.metadata_extractor.detect_document_type")
    def test_filename_has_priority_over_content(self, mock_detect):
        mock_detect.return_value = DocumentType.INVOICE

        metadata = MetadataExtractor.extract(
            "Contract Number: C-001",
            "invoice.pdf",
        )

        mock_detect.assert_called_once_with(
            text="contract number: c-001",
            filename="invoice.pdf",
        )

        assert metadata["document_type"] == DocumentType.INVOICE
