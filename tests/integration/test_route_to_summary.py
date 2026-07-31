from app.graph.builder import ERPAssistantGraph

from tests.factories import make_state


def test_route_to_summary():

    state = make_state(
        needs_research=False,
        requires_clarification=False,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "summarizer"
