from rag_benchmark.diagnostics.reporter import DiagnosticsReporter
from rag_benchmark.reporting.console import print_document_report, print_summary

class DiagnosticsReporter:

    def render(
        self,
        report: DiagnosticsReporter,
        verbose: bool = False,
    ) -> None:

        print_summary(report.summary)

        # print_document_types(report.document_types)

        if verbose:
            for document in report.documents:
                print_document_report(document)

