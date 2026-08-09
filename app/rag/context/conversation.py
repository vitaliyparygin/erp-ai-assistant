from app.agents.state import AgentState


def build_conversation_context(state: AgentState) -> str:
    if not state.messages:
        return "No prior context"

    return "\n".join(
        f"{message.type}: {message.content[:200]}" for message in state.messages[-4:]
    )[:3000]
