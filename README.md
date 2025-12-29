# About

FastAPI service that streams responses from Google Vertex AI (Gemini) through a simple `/ask` endpoint, ready to be consumed via Server-Sent Events (SSE). It includes CORS support, a lightweight HTML client for manual testing, and optional LangSmith traces for tracking usage.

## Features
- FastAPI app with SSE streaming from Google Vertex AI (Gemini) via `google-genai`.
- LangChain/LangSmith instrumentation for run metadata and token usage.
- Simple `/health` endpoint for readiness checks.
- Local HTML page (`index.html`) to try the streaming endpoint without extra tooling.
- Docker dev image with hot-reload friendly `uvicorn` setup.

## Architecture
- API: FastAPI (`src/main.py`) exposing `/ask` (POST, SSE) and `/health` (GET).
- LLM: Google Vertex AI model chosen via `VERTEX_AI_MODEL` (e.g., `gemini-1.5-flash`).
- Observability: LangSmith `RunTree` instrumentation (optional; requires LangSmith env vars if you want traces).
- Frontend: Static HTML page (`index.html`) that streams and renders SSE chunks.

## Requirements
- Python 3.12+
- Google API key with access to the chosen Vertex AI model
- (Optional) LangSmith credentials to record traces

## Configuration
Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your-google-api-key
VERTEX_AI_MODEL=gemini-1.5-flash
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
# Optional LangSmith (for traces)
# LANGCHAIN_API_KEY=your-langsmith-api-key
```

`BACKEND_CORS_ORIGINS` accepts `"*"` for development; restrict it in production.

## Local Development
Install dependencies and run the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `index.html` in a browser and point it to `http://localhost:8000/ask` (default). Update the prompt and click **Start** to see streamed chunks.

## Docker
Build and run with the provided dev Dockerfile (hot-reload enabled via volume mount):

```bash
docker build -t langchain-google-genai -f Dockerfile.dev .
docker run --rm \
	--env-file .env \
	-p 8000:8000 \
	-v "$(pwd)/src:/app/src" \
	langchain-google-genai
```

Alternatively, use the helper script:

```bash
bash ./up.sh
```

## API
- `POST /ask` — Body: `{ "question": "Your prompt" }`. Returns `text/event-stream` where each `data:` line is a chunk and `data: [DONE]` signals completion.
- `GET /health` — Returns `{ "status": "ok" }` for readiness checks.

### SSE example (curl)

```bash
curl -N \
	-H "Content-Type: application/json" \
	-H "Accept: text/event-stream" \
	-d '{"question":"Give me a fun fact about space."}' \
	http://localhost:8000/ask
```

Each chunk arrives as `data: <text>` until `data: [DONE]`.

## Project Structure
- `src/main.py` — FastAPI app with SSE streaming and LangSmith usage tracking.
- `src/example_wrapper.py` — Alternative draft using `langchain_google_genai` wrapper.
- `index.html` — Minimal client for manual streaming tests.
- `Dockerfile.dev` — Dev image for local runs.

## Notes
- Limit `allow_methods`/`allow_headers` in CORS for production.
- To capture traces in LangSmith, set the usual LangSmith environment variables (e.g., `LANGCHAIN_API_KEY`).
- Ensure your Google API key has access to the configured `VERTEX_AI_MODEL`.

## License
This project is licensed under the terms of the LICENSE file in this repository.
