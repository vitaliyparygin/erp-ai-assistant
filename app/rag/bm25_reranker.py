from rank_bm25 import BM25Okapi
import re


def tokenize_text(text: str):
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


class BM25Reranker:

    def rerank(self, query: str, points):

        if not points:
            return points

        corpus = [
            tokenize_text(p.payload.get("content", ""))
            for p in points
        ]

        bm25 = BM25Okapi(corpus)

        query_tokens = tokenize_text(query)

        bm25_scores = bm25.get_scores(query_tokens)

        max_score = max(bm25_scores)

        if max_score > 0:
            bm25_scores = [s / max_score for s in bm25_scores]

        ranked = []

        for point, bm25_score in zip(points, bm25_scores):

            semantic = point.score

            final_score = semantic * 0.6 + bm25_score * 0.4

            ranked.append(
                (
                    final_score,
                    point,
                )
            )

        ranked.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        return [point for _, point in ranked]