import re
from collections import Counter
from rich.table import Table
from rag_benchmark.models import ClassifiedDocument
from rich.console import Console
from rich.markup import escape
console = Console()

LABEL_REGEX = re.compile(
    r"^([A-Za-z][A-Za-z0-9 _/\-]{2,40})\s*:",
    flags=re.MULTILINE,
)

def print_regex_candidates(
    documents: list[ClassifiedDocument],
):

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