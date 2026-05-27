from typing import Literal

from app.graph.state import EmailResearchState


def email_router_agent(state: EmailResearchState) -> EmailResearchState:
    has_links = any(email.links for email in state.get("emails", []))
    has_attachments = any(email.attachments for email in state.get("emails", []))

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
    route = state.get("route", "empty")
    if route == "both":
        return ["link_agent", "attachment_agent"]
    if route == "links":
        return ["link_agent"]
    if route == "attachments":
        return ["attachment_agent"]
    return ["nothing_to_process_agent"]
