from app.rag.retriever.filters import build_retrieval_filter

def test_build_retrieval_filter_returns_none_without_constraints():
    assert build_retrieval_filter() is None


def test_build_retrieval_filter_document_ids():
    filt = build_retrieval_filter(
        document_ids=["doc-1", "doc-2"],
    )

    assert filt is not None
    assert len(filt.must) == 1


def test_build_retrieval_filter_metadata():
    filt = build_retrieval_filter(
        query_metadata={
            "customer_name": "ACME",
            "intent": "ignored",
        },
    )

    assert filt is not None
    assert len(filt.must) == 1
    assert filt.must[0].key == "customer_name"


def test_build_retrieval_filter_combined():
    filt = build_retrieval_filter(
        query_metadata={
            "customer_name": "ACME",
        },
        document_ids=["doc-1"],
    )

    assert filt is not None
    assert len(filt.must) == 2


def test_build_retrieval_filter_ignores_empty_metadata():
    filt = build_retrieval_filter(
        query_metadata={
            "customer_name": "",
            "vendor": None,
        },
    )

    assert filt is None