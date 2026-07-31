from app.graph.builder import ERPAssistantGraph
from tests.factories import make_state


def test_route_to_research():
    state = make_state(
        needs_research=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "research"


def test_route_to_summarizer():
    state = make_state(
        needs_research=False,
        requires_clarification=False,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "summarizer"


def test_route_to_end():
    state = make_state(
        requires_clarification=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "end"
