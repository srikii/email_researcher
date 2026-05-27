from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.attachment_agent import attachment_agent
from app.agents.email_router_agent import email_router_agent, route_documents
from app.agents.gmail_intake_agent import gmail_intake_agent
from app.agents.link_agent import link_agent
from app.agents.nothing_to_process_agent import nothing_to_process_agent
from app.agents.persistence_agent import persistence_agent
from app.agents.summarizer_agent import summarizer_agent
from app.agents.vector_store_agent import vector_store_agent
from app.graph.state import EmailResearchState


def build_graph():
    graph = StateGraph(EmailResearchState)

    graph.add_node("gmail_intake_agent", gmail_intake_agent)
    graph.add_node("email_router_agent", email_router_agent)
    graph.add_node("link_agent", link_agent)
    graph.add_node("attachment_agent", attachment_agent)
    graph.add_node("nothing_to_process_agent", nothing_to_process_agent)
    graph.add_node("summarizer_agent", summarizer_agent)
    graph.add_node("vector_store_agent", vector_store_agent)
    graph.add_node("persistence_agent", persistence_agent)

    graph.add_edge(START, "gmail_intake_agent")
    graph.add_edge("gmail_intake_agent", "email_router_agent")
    graph.add_conditional_edges("email_router_agent", route_documents)
    graph.add_edge("link_agent", "summarizer_agent")
    graph.add_edge("attachment_agent", "summarizer_agent")
    graph.add_edge("nothing_to_process_agent", END)
    graph.add_edge("summarizer_agent", "vector_store_agent")
    graph.add_edge("vector_store_agent", "persistence_agent")
    graph.add_edge("persistence_agent", END)

    return graph.compile()


email_research_graph = build_graph()
