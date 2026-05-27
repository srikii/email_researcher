from app.graph.state import EmailResearchState


def nothing_to_process_agent(state: EmailResearchState) -> EmailResearchState:
    # This path is used when an email has no links and no supported attachments.
    return {"documents": [], "summaries": []}
