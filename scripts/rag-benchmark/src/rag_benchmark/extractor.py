"""Metadata extraction: pulls structured fields out of document text.

The extraction interface is generic (field_name -> regex pattern) so new
document types or fields can be supported by adding a mapping entry rather
than writing new code, keeping the extractor open for extension.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from rag_benchmark.models import ExtractedField, ExtractedMetadata
from rag_benchmark.models import Document as DocumentModel
from rag_benchmark.utils import get_logger, normalize_whitespace

logger = get_logger("extractor")


class MetadataExtractor(ABC):
    """Abstract interface for extracting fields from a classified document."""

    @abstractmethod
    def extract(self, document: DocumentModel, document_type: str) -> ExtractedMetadata:
        """Extract metadata fields for a document of a known type.

        Args:
            document: The document to extract fields from.
            document_type: The classified type, used to select field rules.

        Returns:
            ExtractedMetadata containing whatever fields were found. Fields
            that could not be found are simply omitted (not set to empty).
        """
        raise NotImplementedError


@dataclass(frozen=True)
class FieldRule:
    """A single named field and the regex pattern(s) that can extract it.

    The first capturing group of the first pattern that matches is used as
    the extracted value.
    """

    name: str
    patterns: tuple[str, ...]


# Generic field rules per document type. Domain templates may extend or
# override this mapping via `RegexMetadataExtractor(extra_rules=...)`.
DEFAULT_FIELD_RULES: dict[str, tuple[FieldRule, ...]] = {
    "Invoice": (
        FieldRule("invoice_number", (r"invoice\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("amount", (r"total\s*(?:due|amount)?\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
        FieldRule("customer", (r"bill\s*to\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("currency", (r"\b(USD|EUR|GBP|UAH|PLN)\b",)),
    ),
    "Purchase Order": (
        FieldRule("po_number", (r"(?:p\.?o\.?|purchase\s*order)\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("vendor", (r"vendor\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("amount", (r"total\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
    ),
    "Vendor Profile": (
        FieldRule("vendor", (r"vendor\s*name\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("phone", (r"(?:phone|tel)\s*[:\-]?\s*([\d\-\+\(\) ]{7,})",)),
        FieldRule("email", (r"([\w.\-]+@[\w.\-]+\.\w+)",)),
        FieldRule("address", (r"address\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Employment Contract": (
        FieldRule("contract_number", (r"contract\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("customer", (r"employee\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("contractor", (r"employer\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("start_date", (r"start\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("end_date", (r"end\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Generic Contract": (
        FieldRule("contract_number", (r"contract\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("customer", (r"client\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("contractor", (r"contractor\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("start_date", (r"start\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("end_date", (r"end\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Insurance Policy": (
        FieldRule("policy_number", (r"policy\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("policy_holder", (r"policy\s*holder\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("coverage_period", (r"coverage\s*period\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Service Ticket": (
        FieldRule("ticket_number", (r"ticket\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("status", (r"status\s*[:\-]?\s*([A-Za-z ]+)",)),
        FieldRule("engineer", (r"(?:assigned\s*)?engineer\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Bank Statement": (
        FieldRule("account_number", (r"account\s*(?:no|number)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("statement_period", (r"statement\s*period\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("balance", (r"(?:closing\s*)?balance\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
    ),
    "CRM Opportunity": (
        FieldRule("opportunity_name", (r"opportunity\s*name\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("stage", (r"(?:deal\s*)?stage\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("value", (r"value\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
    ),
    "Project Report": (
        FieldRule("project_name", (r"project\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("status", (r"status\s*[:\-]?\s*([A-Za-z ]+)",)),
    ),
    "Meeting Minutes": (
        FieldRule("meeting_date", (r"date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("attendees", (r"attendees\s*[:\-]?\s*([^\n]+)",)),
    ),
}


class RegexMetadataExtractor(MetadataExtractor):
    """Extracts fields using per-document-type regex rules.

    Args:
        extra_rules: Additional or overriding field rules, keyed by
            document_type, merged on top of DEFAULT_FIELD_RULES. This is
            the extension point used by domain-specific templates (e.g.
            the ERP template can add PO-specific fields).
    """

    def __init__(self, extra_rules: dict[str, tuple[FieldRule, ...]] | None = None) -> None:
        self._rules: dict[str, tuple[FieldRule, ...]] = dict(DEFAULT_FIELD_RULES)
        if extra_rules:
            for doc_type, rules in extra_rules.items():
                base = self._rules.get(doc_type, ())
                # Merge by field name so a template can override a generic
                # rule's regex without producing a duplicate entry for the
                # same field (which would otherwise double-count that field
                # in expected_fields(), coverage stats, and reports).
                merged: dict[str, FieldRule] = {rule.name: rule for rule in base}
                for rule in rules:
                    merged[rule.name] = rule
                self._rules[doc_type] = tuple(merged.values())

    def extract(self, document: DocumentModel, document_type: str) -> ExtractedMetadata:
        rules = self._rules.get(document_type, ())
        fields: dict[str, ExtractedField] = {}

        for rule in rules:
            for pattern in rule.patterns:
                match = re.search(pattern, document.text, flags=re.IGNORECASE)
                if match and match.groups():
                    value = normalize_whitespace(match.group(1))
                    if value:
                        fields[rule.name] = ExtractedField(name=rule.name, value=value)
                        break

        if not fields and rules:
            logger.debug(
                "No fields extracted for %s (type=%s)", document.filename, document_type
            )

        return ExtractedMetadata(
            document_id=document.id, document_type=document_type, fields=fields
        )

    def expected_fields(self, document_type: str) -> list[str]:
        """Return the field names this extractor knows how to extract for a type.

        Used by the diagnostics subsystem to compute metadata coverage
        (fields expected vs. fields actually extracted) without needing to
        know anything about regex internals.

        Args:
            document_type: The classified document type to look up.

        Returns:
            Field names in rule-definition order, or an empty list if no
            rules are registered for this document type.
        """
        return [rule.name for rule in self._rules.get(document_type, ())]