from __future__ import annotations
from collections import Counter
from rag_benchmark.diagnostics.models import RegexCandidate

class RegexCandidateAnalyzer:

    @staticmethod
    def extract_candidate_labels(text: str) -> Counter[str]:
        """Extract possible metadata labels from raw document text."""

        labels = Counter()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                continue
            label = line.split(":", 1)[0].strip()
            if 2 <= len(label) <= 40:
                labels[label] += 1

        return labels


    @staticmethod
    def collect_candidates(text: str) -> Counter[str]:
        counter = Counter()

        for line in text.splitlines():
            if ":" not in line:
                continue

            label = line.split(":", 1)[0].strip()

            counter[label] += 1

        return [
            RegexCandidate(
                label=label,
                count=count,
            )
            for label, count in counter.items()
        ]


    @staticmethod
    def collect_candidates_from_documents(
            texts: list[str],
    ) -> Counter[str]:
        counter: Counter[str] = Counter()

        for text in texts:
            counter.update(
                RegexCandidateAnalyzer.collect_candidates(text)
            )

        return counter