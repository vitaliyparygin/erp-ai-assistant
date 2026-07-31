from app.agents.state import AgentState


def make_state(**kwargs):
    state = AgentState(
        session_id="test",
        query="invoice",
        original_query="invoice",
    )

    for k, v in kwargs.items():
        setattr(state, k, v)

    return state
