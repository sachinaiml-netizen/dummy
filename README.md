# ProjectIQ — AI Knowledge Assistant

A client-demo prototype for small businesses that need a document-grounded internal knowledge assistant.

## What it demonstrates

- PDF upload and text extraction
- Document-grounded question answering
- Source references in responses
- FastAPI REST endpoints
- A responsive web interface
- Existing project-risk intelligence API

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## API

`POST /assistant/upload` — index a PDF into the in-memory knowledge base.

`POST /assistant/query` — ask a question against the indexed documents.

`POST /risk` — existing explainable project-risk assessment endpoint.

## Important

This is a demonstration prototype. The retrieval layer is intentionally lightweight and runs in memory. A production version would add persistent storage, authentication, proper chunking/embeddings, an LLM provider, and tenant isolation.
