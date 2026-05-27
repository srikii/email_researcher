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


gmail_intake_agent adds emails. Each email has metadata, body text, links, and downloaded attachment paths.

email_router_agent adds route: links, attachments, both, or empty.

link_agent adds extracted URL documents to documents.

attachment_agent adds extracted PDF/Word documents to documents.

summarizer_agent reads all email documents and adds summaries.

vector_store_agent embeds summary and extracted document text into Chroma and adds stored_vector_ids.

persistence_agent saves summaries to SQLite and adds saved_summary_ids.

LangSmith traces each LangGraph node when LANGSMITH_TRACING=true, LANGSMITH_API_KEY is set, and the model calls run through LangChain.
