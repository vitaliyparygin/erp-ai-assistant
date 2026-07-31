from app.graph.builder import ERPAssistantGraph

from tests.factories import make_state


def test_route_to_research():

    state = make_state(
        needs_research=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "research"
