import re
from collections import Counter, defaultdict
from rich.table import Table
from rich.markup import escape
from rag_benchmark.models import ClassifiedDocument
from rag_benchmark.templates import TemplateDefinition
from rag_benchmark.diagnostics.models import RegexStat, DocumentDiagnostic, RegexCandidate
from rich.text import Text

from rag_benchmark.suggestions.regex_suggestions import build_regex
from rich.console import Console
console = Console()
LABEL_REGEX = re.compile(
    r"^([A-Za-z][A-Za-z0-9 _/\-]{2,40})\s*:",
    flags=re.MULTILINE,
)
FIELD_REGEX_HINTS: dict[str, list[str]] = {
    "amount": [
        "Amount",
        "Total",
        "Grand Total",
        "Balance Due",
        "Subtotal",
    ],
    "invoice_number": [
        "Invoice Number",
        "Invoice No",
        "Invoice #",
    ],
    "contract_number": [
        "Contract Number",
        "Agreement Number",
        "Reference Number",
    ],
    "customer": [
        "Customer",
        "Client",
        "Buyer",
        "Account Holder",
    ],
    "vendor": [
        "Vendor",
        "Supplier",
        "Seller",
        "Provider",
    ],
    "ticket_number": [
        "Ticket Number",
        "Case Number",
        "Reference",
    ],
    "priority": [
        "Priority",
        "Priority Level",
    ],
    "status": [
        "Status",
        "Current Status",
        "State",
    ],
    "delivery_date": [
        "Delivery Date",
        "Ship Date",
        "Expected Delivery",
    ],
    "due_date": [
        "Due Date",
        "Payment Due",
    ],
    "start_date": [
        "Start Date",
        "Effective Date",
        "Commencement Date",
    ],
    "end_date": [
        "End Date",
        "Expiration Date",
        "Termination Date",
    ],
}
def regex_text(regex: str) -> Text:
    return Text(regex)




class RegexAnalyzer:

    @staticmethod
    def analyze(
        classified: ClassifiedDocument,
        template: TemplateDefinition,
    ) -> list[RegexStat]:

        stats: list[RegexStat] = []
        doc = classified

        rules = template.extraction_rules.get(
            doc.classification.document_type,
            (),
        )

        text = doc.document.text
        for rule in rules:
            for pattern in rule.patterns:
                found = re.findall(
                    pattern,
                    text,
                    flags=re.IGNORECASE | re.MULTILINE,
                )
                value = None

                if found:
                    first = found[0]

                    if isinstance(first, tuple):
                        value = first[0]
                    else:
                        value = first
                field = getattr(rule, "name", None) or getattr(rule, "field_name")
                stats.append(
                    RegexStat(
                        document_type=doc.classification.document_type,
                        field=field,
                        pattern=pattern,
                        matched=bool(found),
                        matches = 1 if found else 0,
                        matched_text=found,
                        value=len(found) if found else None,
                    )
                )


        return stats






    # @staticmethod
    @staticmethod
    def field_suggestions(field: str) -> list[tuple[str, str]]:
        labels = FIELD_REGEX_HINTS.get(field, [])

        return [
            (label, build_regex(label))
            for label in labels
        ]

    @staticmethod
    def find_candidate_labels(text: str) -> Counter[str]:
        """
        Return possible field labels found in document text.
        """

        labels = Counter()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                label = line.split(":", 1)[0].strip()
                if 2 <= len(label) <= 40:
                    labels[label] += 1

        return labels

