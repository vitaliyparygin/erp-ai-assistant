from rich.console import Console
from rich.table import Table
from rag_benchmark.models import DocumentDiagnostics, Summary

console = Console()


def print_document_report(document_name, document_type, extracted, required):
    console.rule(f"[bold cyan]{document_name}")

    console.print(f"[green]Classification[/green]")
    console.print(f"✔ {document_type}")
    console.print()

    table = Table(title="Extraction")

    table.add_column("Field")
    table.add_column("Status")

    generated = 0
    skipped = 0

    for field in required:

        if field in extracted:

            table.add_row(field, "[green]✔[/green]")
            generated += 1

        else:

            table.add_row(field, "[red]✘[/red]")
            skipped += 1

    console.print(table)

    coverage = (
        generated / len(required) * 100
        if required
        else 100
    )
    console.print()

    console.print(f"Questions generated : {generated}")
    console.print(f"Questions skipped   : {skipped}")
    console.print(f"Coverage            : {coverage:.0f}%")


def print_summary(
    total_docs,
    classified_docs,
    extracted_fields,
    total_fields,
    generated_questions,
    skipped_questions,
):
    table = Table(title="Benchmark Diagnose Summary")

    table.add_column("Metric")
    table.add_column("Value")

    table.add_row(
        "Documents classified",
        f"{classified_docs}/{total_docs} ({classified_docs/total_docs:.0%})",
    )

    table.add_row(
        "Fields extracted",
        f"{extracted_fields}/{total_fields} ({extracted_fields/total_fields:.0%})",
    )

    table.add_row(
        "Questions generated",
        str(generated_questions),
    )

    table.add_row(
        "Questions skipped",
        str(skipped_questions),
    )

    table.add_row(
        "Coverage score",
        f"{generated_questions/(generated_questions+skipped_questions):.0%}",
    )

    console.print()
    console.print(table)


# def print_document_types(...):
#     ...
#
#
# def print_missing_fields(...):
#     ...
#
#
# def print_recommendations(...):
#     ...