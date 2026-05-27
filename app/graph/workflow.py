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
    # StateGraph is LangGraph's way to define a workflow.
    # Every node is one Python function that accepts and returns state.
    graph = StateGraph(EmailResearchState)

    # Register all agents by name. These names also show up in stream updates.
    graph.add_node("gmail_intake_agent", gmail_intake_agent)
    graph.add_node("email_router_agent", email_router_agent)
    graph.add_node("link_agent", link_agent)
    graph.add_node("attachment_agent", attachment_agent)
    graph.add_node("nothing_to_process_agent", nothing_to_process_agent)
    graph.add_node("summarizer_agent", summarizer_agent)
    graph.add_node("vector_store_agent", vector_store_agent)
    graph.add_node("persistence_agent", persistence_agent)

    # The graph always starts by reading Gmail.
    graph.add_edge(START, "gmail_intake_agent")
    graph.add_edge("gmail_intake_agent", "email_router_agent")

    # The router decides whether we need link processing, attachment processing,
    # both, or nothing.
    graph.add_conditional_edges("email_router_agent", route_documents)

    # Both link_agent and attachment_agent feed into the same summarizer.
    graph.add_edge("link_agent", "summarizer_agent")
    graph.add_edge("attachment_agent", "summarizer_agent")
    graph.add_edge("nothing_to_process_agent", END)
    graph.add_edge("summarizer_agent", "vector_store_agent")
    graph.add_edge("vector_store_agent", "persistence_agent")
    graph.add_edge("persistence_agent", END)

    # compile() turns the graph definition into something we can run.
    return graph.compile()


# Keep one compiled graph ready for FastAPI and scripts to use.
email_research_graph = build_graph()
