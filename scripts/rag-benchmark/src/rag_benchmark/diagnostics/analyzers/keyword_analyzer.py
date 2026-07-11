
from __future__ import annotations
from rag_benchmark.models import ClassifiedDocument
from rag_benchmark.diagnostics.models import MatchedKeyword





class KeywordAnalyzer:

    @staticmethod
    def analyze(
        classified: ClassifiedDocument,
    ) -> list[MatchedKeyword]:

        result = []
        print(type(classified.classification))
        print(classified.classification)
        print(classified.classification.model_dump())
        scores = classified.classification.scores

        for doc_type, score in sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        ):

            result.append(
                MatchedKeyword(
                    document_type=doc_type,
                    score=score,
                )
            )

        return result