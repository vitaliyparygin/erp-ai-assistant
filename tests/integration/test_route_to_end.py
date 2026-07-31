from app.graph.builder import ERPAssistantGraph

from tests.factories import make_state


def test_route_to_end():

    state = make_state(
        requires_clarification=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "end"
