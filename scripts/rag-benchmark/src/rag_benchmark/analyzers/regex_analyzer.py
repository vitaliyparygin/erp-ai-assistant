import re
from collections import Counter
from rag_benchmark.models import ClassifiedDocument
from rag_benchmark.templates import TemplateDefinition
from rich.console import Console
from rich.table import Table
from rag_benchmark.diagnostics.models import RegexStat

console = Console()
LABEL_REGEX = re.compile(
    r"^([A-Za-z][A-Za-z0-9 _/\-]{2,40})\s*:",
    flags=re.MULTILINE,
)


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
                        matches=len(found),
                        value=value,
                        matched=len(found) > 0
                    )
                )

        return stats

    @staticmethod
    def report_unused(stats: list[RegexStat]) -> None:
        """Print regexes that never matched and return their count."""
        unused = [s for s in stats if s.matches == 0]
        if not unused:
            return 0
        table = Table(title="Unused regexes")
        table.add_column("Document")
        table.add_column("Field")
        table.add_column("Regex")

        for stat in unused:
            table.add_row(
                stat.document_type,
                stat.field,
                stat.pattern,
            )
        console.print(table)
        console.print(f"\nUnused regexes: {len(unused)}")

    @staticmethod
    def suggest(stats: list[RegexStat]) -> None:
        counter = Counter()
        for doc in stats:
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
                regex,
            )

        console.print(table)
