# email_researcher
This prototype reads Gmail messages, finds links and PDF/Word attachments, extracts their content, summarizes everything, stores the summary in SQLite, and stores searchable semantic chunks in Chroma.

The LangGraph state is the shared envelope passed between agents. Each agent returns only the fields it changed. LangGraph merges those changes into the next state.

Setup
Install Python 3.11 or 3.12.

Recreate the virtual environment if the old one is broken:

Remove-Item -Recurse -Force myvenv
py -3.12 -m venv myvenv
.\myvenv\Scripts\Activate.ps1
pip install -r requirements.txt
crawl4ai-setup
Copy .env.example to .env and fill in your keys.

Create a Google Cloud OAuth Desktop app, enable Gmail API, and download it as credentials.json.

Authorize Gmail:

python scripts\authorize_gmail.py
Start the app:

uvicorn app.api.main:app --reload
Open http://127.0.0.1:8000.

Important Files
email_research/
  app/
    agents/
      attachment_agent.py
      email_router_agent.py
      gmail_intake_agent.py
      link_agent.py
      nothing_to_process_agent.py
      persistence_agent.py
      summarizer_agent.py
      vector_store_agent.py
    api/main.py
    gmail/client.py
    graph/state.py
    graph/workflow.py
    storage/chroma_store.py
    storage/sqlite_store.py
    static/
      index.html
      styles.css
      app.js
  docs/BEGINNER_GUIDE.md
  scripts/
    authorize_gmail.py
    process_once.py
  requirements.txt
  .env.example
app/graph/workflow.py wires the multi-agent LangGraph.
app/graph/state.py defines the state that moves between agents.
app/agents/link_agent.py crawls URLs with crawl4ai.
app/agents/attachment_agent.py reads PDF and Word attachments.
app/agents/summarizer_agent.py creates the final summary with an LLM.
app/agents/vector_store_agent.py saves searchable semantic content in Chroma.
app/storage/chroma_store.py runs semantic search.
app/api/main.py exposes the web app and backend API.
API
POST /process processes recent matching Gmail messages.
GET /process/stream processes recent matching Gmail messages and streams node progress for the web UI.
GET /summaries lists generated summaries.
GET /summaries/{email_id} returns one summary.
POST /search semantic search over email summaries and extracted content.
Example search:

{
  "query": "the funny cat video John sent last month",
  "limit": 5
}
How The Agents Pass Data
The graph starts with a small state:

{"gmail_query": "...", "max_results": 10}
gmail_intake_agent adds emails. Each email has metadata, body text, links, and downloaded attachment paths.

email_router_agent adds route: links, attachments, both, or empty.

link_agent adds extracted URL documents to documents.

attachment_agent adds extracted PDF/Word documents to documents.

summarizer_agent reads all email documents and adds summaries.

vector_store_agent embeds summary and extracted document text into Chroma and adds stored_vector_ids.

persistence_agent saves summaries to SQLite and adds saved_summary_ids.

LangSmith traces each LangGraph node when LANGSMITH_TRACING=true, LANGSMITH_API_KEY is set, and the model calls run through LangChain.
