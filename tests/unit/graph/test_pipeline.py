from unittest.mock import MagicMock


def test_pipeline_order():
    retriever = MagicMock(return_value="docs")
    research = MagicMock(return_value="research")
    summarize = MagicMock(return_value="summary")
    citation = MagicMock(return_value="answer")

    docs = retriever()

    research_result = research(docs)

    summary = summarize(research_result)

    answer = citation(summary)

    retriever.assert_called_once()
    research.assert_called_once()
    summarize.assert_called_once()
    citation.assert_called_once()

    assert answer == "answer"
