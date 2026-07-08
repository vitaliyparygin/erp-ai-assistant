from rich.console import Console
from rich.table import Table

from .regex_analyzer import RegexStat


console = Console()


def report_unused_regexes(stats: list[RegexStat]):

    table = Table(title="Unused regexes")

    table.add_column("Document")
    table.add_column("Field")
    table.add_column("Regex")

    count = 0

    for s in stats:

        if s.matches == 0:

            table.add_row(
                s.document_type,
                s.field,
                s.pattern,
            )

            count += 1

    console.print(table)

    console.print(f"\nUnused regexes: {count}")