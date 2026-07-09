import re
from collections import Counter, defaultdict
from rich.console import Console
from rich.table import Table
from rich.markup import escape
from rag_benchmark.models import ClassifiedDocument
from rag_benchmark.templates import TemplateDefinition
from rag_benchmark.diagnostics.models import RegexStat, DocumentDiagnostic
from rich.text import Text

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

def build_regex(label: str) -> str:
    escaped = re.escape(label)

    lower = label.lower()

    if "date" in lower:
        value = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"

    elif any(x in lower for x in ("amount", "total", "balance", "price")):
        value = r"([$€£]?\s?[0-9][0-9,\.]*)"

    elif "email" in lower:
        value = r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"

    elif "phone" in lower:
        value = r"([\+\d][\d\-\(\)\s]{6,})"

    else:
        value = r"(.+)"

    return rf"{escaped}\s*[:\-]?\s*{value}"


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
                stats.append(
                    RegexStat(
                        document_type=doc.classification.document_type,
                        field=rule.name,
                        pattern=pattern,
                        matched=bool(found),
                        matches = 1 if found else 0,
                        matched_text=found,
                        value=len(found) if found else None,
                    )
                )


        return stats

    @staticmethod
    def report_unused(stats: list[RegexStat]) -> None:
        """Print regexes that never matched and return their count."""
        unused = [s for s in stats if not s.matched]
        if not unused:
            return 0
        table = Table(title="Regex Success Rate")
        table.add_column("Document")
        table.add_column("Field")
        table.add_column("Regex")

        for stat in unused:
            table.add_row(
                stat.document_type,
                stat.field,
                escape(stat.pattern),
            )
        console.print(table)
        console.print(f"\nUnused regexes: {len(unused)}")

    def print_regex_analysis(
            diagnostics: list[DocumentDiagnostic],
    ):
        console.rule("Regex Analysis")
        for diag in diagnostics:
            if not diag.regex_stats:
                continue
            console.print(f"\n[bold]{diag.filename}[/bold]")
            grouped = defaultdict(list)
            for stat in diag.regex_stats:
                grouped[stat.field].append(stat)
            for field, stats in grouped.items():
                console.print(f"\n[cyan]{field}[/cyan]")
                for stat in stats:
                    if stat.matched:
                        console.print(
                            f"[green]✓[/green] {stat.pattern}"
                        )
                        if stat.matched_text:
                            console.print(
                                f"    matched : {stat.matched_text}"
                            )
                        if stat.value:
                            console.print(
                                f"    value   : {stat.value}"
                            )
                    else:
                        console.print(
                            f"[red]✗[/red] {stat.pattern}"
                        )
    @staticmethod
    def suggest(documents: list[ClassifiedDocument]) -> None:
        counter = Counter()
        for doc in documents:
            text = doc.document.text
            for match in LABEL_REGEX.finditer(text):
                label = match.group(1).strip()
                counter[label] += 1

        table = Table(title="Suggested regex candidates")
        table.add_column("Label")
        table.add_column("Occurrences")
        table.add_column("Suggested regex")

        for label, cnt in counter.most_common():
            regex = rf"{re.escape(label)}\s*[:\-]?\s*(.+)"
            table.add_row(
                label,
                str(cnt),
                escape(regex),
            )

        console.print(table)





    @staticmethod
    def collect_regex_candidates(labels: Counter[str]) -> None:
        table = Table(title="Suggested Regex")

        table.add_column("Label")
        table.add_column("Occurrences")
        table.add_column("Regex")

        for label, count in labels.most_common():
            table.add_row(
                label,
                str(count),
                regex_text(build_regex(label)),
            )

        console.print(table)

    # @staticmethod
    @staticmethod
    def field_suggestions(field: str) -> list[tuple[str, str]]:
        labels = FIELD_REGEX_HINTS.get(field, [])

        return [
            (label, build_regex(label))
            for label in labels
        ]