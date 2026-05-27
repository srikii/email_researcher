from typing import Literal

from app.graph.state import EmailResearchState


def email_router_agent(state: EmailResearchState) -> EmailResearchState:
    # Look through the emails and decide which worker agents are needed.
    has_links = False
    has_attachments = False

    for email in state.get("emails", []):
        if email.links:
            has_links = True
        if email.attachments:
            has_attachments = True

    if has_links and has_attachments:
        route = "both"
    elif has_links:
        route = "links"
    elif has_attachments:
        route = "attachments"
    else:
        route = "empty"

    return {"route": route}


def route_documents(state: EmailResearchState) -> list[Literal["link_agent", "attachment_agent", "nothing_to_process_agent"]]:
    # LangGraph calls this function after email_router_agent.
    # The returned node names decide the next path through the graph.
    route = state.get("route", "empty")
    if route == "both":
        return ["link_agent", "attachment_agent"]
    if route == "links":
        return ["link_agent"]
    if route == "attachments":
        return ["attachment_agent"]
    return ["nothing_to_process_agent"]
