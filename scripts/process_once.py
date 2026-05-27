from app.config import get_settings
from app.graph.workflow import email_research_graph


if __name__ == "__main__":
    settings = get_settings()
    result = email_research_graph.invoke(
        {"gmail_query": settings.gmail_query, "max_results": settings.gmail_max_results}
    )
    print(result)
