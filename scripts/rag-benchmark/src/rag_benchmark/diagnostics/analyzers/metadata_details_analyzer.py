
from __future__ import annotations
from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.diagnostics.models import MetadataDetail


class MetadataDetailsAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,
    ) -> list[MetadataDetail]:

        rows = []

        stats = {
            s.field: s
            for s in result.regex_stats
        }

        extracted = result.classified.metadata.fields

        for field in result.expected_fields:

            value = extracted.get(field)

            regex = stats.get(field)

            rows.append(
                MetadataDetail(
                    field=field,
                    matched=value is not None,
                    regex=regex.pattern if regex else "",
                    extracted_value=value.value if value else "",
                )
            )

        return rows