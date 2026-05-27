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


Beginner Guide
This app is a multi-agent pipeline. In LangGraph, an "agent" can simply be a Python function that receives shared state, does one job, and returns updates to that state.

The State
app/graph/state.py defines EmailResearchState.

Think of state like a backpack that moves from agent to agent:

gmail_query: what to search in Gmail.
max_results: how many emails to process.
emails: messages fetched from Gmail.
route: tells the graph whether the emails have links, attachments, both, or nothing useful.
documents: extracted text from crawled URLs and attachments.
summaries: final human-friendly summaries.
stored_vector_ids: Chroma IDs created after embedding.
saved_summary_ids: SQLite summary IDs.
errors: non-fatal failures.
documents and errors use Annotated[..., operator.add]. That tells LangGraph to merge lists when multiple agents run in parallel. This matters when one email has links and attachments: link_agent and attachment_agent can both add documents.

The Graph
app/graph/workflow.py wires the agents:

gmail_intake_agent
Fetches emails and downloads attachments.

email_router_agent
Looks at the fetched emails and decides which workers are needed.

link_agent
Uses crawl4ai to open URLs and return page text.

attachment_agent
Reads PDF and Word files from disk and returns extracted text.

summarizer_agent
Groups extracted documents by email and asks the LLM for a structured summary.

vector_store_agent
Embeds the summary and source text, then stores vectors in Chroma.

persistence_agent
Saves the user-facing summaries in SQLite so the web app can list them quickly.

Why FastAPI
FastAPI gives you a backend that a Flutter app can call later. The current web UI is intentionally simple:

Click Process Gmail to run the graph.
Use the search box to run semantic search over Chroma.
View generated summaries from SQLite.
When you build Flutter later, keep the backend and replace only app/static.

Why SQLite And Chroma
SQLite stores exact records:

subject
sender
date
short summary
detailed summary
source URLs/files
Chroma stores meaning:

"funny cat video from John" can match an email even when the exact words differ.
"document Max sent last month" can match the attached document summary and metadata.
You use both because they answer different kinds of questions.

LangSmith
LangSmith tracing is controlled by environment variables:
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2-your-key
LANGSMITH_PROJECT=email-research-agent

When the graph runs, LangChain model and embedding calls are traced. This helps you see inputs, outputs, timing, and failures.

Adding More Agents Later
Good next agents:

dedupe_agent: skip emails already processed.
policy_agent: block suspicious URLs or huge files.
image_ocr_agent: extract text from image attachments.
entity_agent: extract people, companies, dates, and tasks.
notification_agent: push completed summaries to Flutter.
The pattern is always the same:

Add fields to EmailResearchState if needed.
Create a function in app/agents.
Add it to app/graph/workflow.py.
Return only the state fields the agent updates..

LangSmith traces each LangGraph node when LANGSMITH_TRACING=true, LANGSMITH_API_KEY is set, and the model calls run through LangChain.
