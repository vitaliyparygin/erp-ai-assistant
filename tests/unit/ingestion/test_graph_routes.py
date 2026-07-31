import pytest
from tests.factories import make_state
from app.graph.builder import ERPAssistantGraph


@pytest.mark.parametrize(
    "clarification,sufficient,research,expected",
    [
        (False, True, False, "summarizer"),
        (False, False, True, "research"),
        (True, False, False, "end"),
        (True, True, False, "end"),
        (False, True, True, "research"),
    ],
)
def test_route_after_retrieval(
    clarification,
    sufficient,
    research,
    expected,
):

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    state = make_state(
        requires_clarification=clarification,
        has_sufficient_context=sufficient,
        needs_research=research,
    )

    assert graph._route_after_retrieval(state) == expected


def test_clarification_has_priority():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    state = make_state(
        requires_clarification=True,
        has_sufficient_context=True,
        needs_research=False,
    )

    assert graph._route_after_retrieval(state) == "end"


def test_research_priority():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    state = make_state(
        requires_clarification=False,
        has_sufficient_context=True,
        needs_research=True,
    )

    assert graph._route_after_retrieval(state) == "research"


def test_unknown_state_defaults_to_summary():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    state = make_state()

    assert graph._route_after_retrieval(state) == "summarizer"
