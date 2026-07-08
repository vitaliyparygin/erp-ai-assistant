from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from rag_benchmark.models import ClassifiedDocument
from rag_benchmark.templates import TemplateDefinition


@dataclass
class RegexStat:
    document_type: str
    field: str
    pattern: str
    matches: int
    matched: bool
    value: str | None

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