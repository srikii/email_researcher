# Beginner Guide

This app is a multi-agent pipeline. In LangGraph, an "agent" can simply be a Python function that receives shared state, does one job, and returns updates to that state.

## The State

`app/graph/state.py` defines `EmailResearchState`.

Think of state like a backpack that moves from agent to agent:

- `gmail_query`: what to search in Gmail.
- `max_results`: how many emails to process.
- `since` / `until`: optional user-defined time window.
- `emails`: messages fetched from Gmail.
- `route`: tells the graph whether the emails have links, attachments, both, or nothing useful.
- `documents`: extracted text from crawled URLs and attachments.
- `summaries`: final human-friendly summaries.
- `stored_vector_ids`: Chroma IDs created after embedding.
- `saved_summary_ids`: SQLite summary IDs.
- `errors`: non-fatal failures.

`documents` and `errors` use `Annotated[..., operator.add]`. That tells LangGraph to merge lists when multiple agents run in parallel. This matters when one email has links and attachments: `link_agent` and `attachment_agent` can both add documents.

## The Graph

`app/graph/workflow.py` wires the agents:

1. `gmail_intake_agent`
   Fetches emails after the saved cursor or inside a selected time range, then downloads attachments.

2. `email_router_agent`
   Looks at the fetched emails and decides which workers are needed.

3. `link_agent`
   Uses crawl4ai to open URLs and return page text.

4. `attachment_agent`
   Reads PDF and Word files from disk and returns extracted text.

5. `summarizer_agent`
   Groups extracted documents by email and asks the LLM for a structured summary.

6. `vector_store_agent`
   Embeds the summary and source text, then stores vectors in Chroma.

7. `persistence_agent`
   Saves the user-facing summaries in SQLite so the web app can list them quickly.

## Why FastAPI

FastAPI gives a backend that a Flutter app mobile app can call later. The current web UI is intentionally simple:

- Click `Process Gmail` to run the graph only for new emails from now onward.
- Pick `From` and `Until`, then click `View Range` to see already-generated summaries for that window.
- Pick `From` and `Until`, then click `Process Range` to summarize emails in that window.
- Use the search box to run semantic search over Chroma.
- View generated summaries from SQLite.

When you build Flutter later, keep the backend and replace only `app/static`.

## Why SQLite And Chroma

SQLite stores exact records:

- subject
- sender
- date
- short summary
- detailed summary
- source URLs/files

Chroma stores meaning:

- "funny cat video from John" can match an email even when the exact words differ.
- "document Max sent last month" can match the attached document summary and metadata.

You use both because they answer different kinds of questions.

## From Now Onward Behavior

The app stores a cursor named `gmail_cursor_started_at` in SQLite. On the first startup, that cursor is set to the current time. That is what prevents the prototype from processing every old email in your Gmail account.

When you click `Process Gmail`:

1. The API reads the cursor.
2. Gmail is queried for messages after that cursor.
3. The graph summarizes matching messages.
4. The cursor advances to the time the run started.

The selected date range controls are separate. They are for manual review/backfill and do not move the cursor.

## LangSmith

LangSmith tracing is controlled by environment variables:

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2-your-key
LANGSMITH_PROJECT=email-research-agent
```

When the graph runs, LangChain model and embedding calls are traced. This helps you see inputs, outputs, timing, and failures.

## Adding More Agents Later

Good next agents:

- `dedupe_agent`: skip emails already processed.
- `policy_agent`: block suspicious URLs or huge files.
- `image_ocr_agent`: extract text from image attachments.
- `entity_agent`: extract people, companies, dates, and tasks.
- `notification_agent`: push completed summaries to Flutter.

The pattern is always the same:

1. Add fields to `EmailResearchState` if needed.
2. Create a function in `app/agents`.
3. Add it to `app/graph/workflow.py`.
4. Return only the state fields the agent updates.
