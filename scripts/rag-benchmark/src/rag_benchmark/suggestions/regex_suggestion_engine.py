from rag_benchmark.models import ClassifiedDocument
from collections import Counter
import re
from rich.table import Table
from rich.console import Console
from rich.markup import escape
from rag_benchmark.suggestions.regex_suggestions import (
    suggest_field_synonyms,
)
console = Console()


LABEL_REGEX = re.compile(
    r"^([A-Za-z][A-Za-z0-9 _/\-]{2,40})\s*:",
    flags=re.MULTILINE,
)

class RegexSuggestionEngine:


    @staticmethod
    def render_dataset_suggestions(documents: list[ClassifiedDocument]) -> None:
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
    def render_field_suggestions(field: str) -> None:
        hints = suggest_field_synonyms(field)

        if hints:
            console.print(
                f"[yellow]{field}[/yellow]: add regex for "
                + ", ".join(hints)
            )
        else:
            console.print(
                f"[yellow]{field}[/yellow]: "
                "no synonym hints available"
            )