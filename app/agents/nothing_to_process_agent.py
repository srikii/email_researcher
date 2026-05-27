from app.graph.state import EmailResearchState


def nothing_to_process_agent(state: EmailResearchState) -> EmailResearchState:
    return {"documents": [], "summaries": []}
