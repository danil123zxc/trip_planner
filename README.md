# Trip Planner

Trip Planner is an agentic travel planning platform built around a LangGraph workflow extracted from [trip planner notebook](trip_planner.ipynb). The system coordinates multiple research agents (lodging, activities, food, transport, and advisory) to assemble a day-by-day itinerary, supports human-in-the-loop decisions, and exposes the workflow through a FastAPI service.

# Workflow's diagram 

![trip_planner_diagram](trip_planner_diagram.png)


## Key Capabilities

- **LangGraph Orchestration** - stateful workflow that estimates budget, plans research, fans out to specialised agents, and synthesises a final itinerary.
- **Retrieval-Augmented Research** - shared RAG pipeline that powers internet, Reddit, and internal vector store search tools.
- **Human-in-the-Loop** - interrupt nodes pause execution so users can choose preferred options or adjust research plans before resuming.
- **Extensible API Layer** - `/plan/start` and `/plan/resume/{thread_id}` endpoints wrap the notebook logic for production use.
- **Modular Codebase** - reusable helpers live under `src/` and are covered by unit tests in `tests/`.

## Repository Layout

- `trip_planner.ipynb` - canonical notebook describing the end-to-end flow
- `src/` - Python modules extracted from the notebook
  - `api/` - FastAPI application (start/resume endpoints)
  - `core/` - Pydantic models, shared domain types, config
  - `pipelines/` - Retrieval pipeline assembly
  - `services/` - External integrations (TripAdvisor, Amadeus, geocoding)
  - `tools/` - Search tools wired into the agents
  - `workflows/` - LangGraph nodes and compilation helpers
- `tests/` - Pytest suite (domain, services, workflow, API)
- `docs/` - Feature-sliced architecture documentation
- `data/` - Shared datasets (create as needed)
- `artifacts/` - Generated maps, CSVs, cached runs (git-ignored)

## Prerequisites

- Python 3.12
- Access tokens for external services:
  - `OPENAI_API_KEY`
  - `TAVILY_API_KEY`
  - `XAI_API_KEY` (xAI Grok models)
  - `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`
  - `TRIP_ADVISOR_API_KEY`
  - `AMADEUS_API_KEY` / `AMADEUS_API_SECRET`

Set these values in `.env` or your shell before running the API or notebook.

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

After modifying dependencies, refresh the lock file: `pip freeze > requirements.txt`.

## Running the Notebook

1. Launch Jupyter Lab: `jupyter lab`
2. Open `trip_planner.ipynb`
3. Ensure environment variables are loaded (see `.env`)
4. Execute cells top-to-bottom. Before committing, verify with:
   ```bash
   jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb
   ```

## FastAPI Service

### Start the API

```bash
source .venv/bin/activate
uvicorn src.api.app:app --reload
```

### Endpoints

- `POST /plan/start`
  - Body: `context` (trip configuration), optional `thread_id`, optional `user_prompt`
  - Returns: planning status (`interrupt`, `complete`, `needs_follow_up`, `no_plan`), LangGraph config, agent outputs, and interrupt payload when human input is required.

- `POST /plan/resume/{thread_id}`
  - Body: optional `config`, `selections` (indexes of chosen options), optional `research_plan` overrides.
  - Uses stored state to resume the graph and returns updated status and payloads.

- `GET /health`
  - Simple readiness probe.

### Human-in-the-Loop Flow

1. Call `/plan/start` with a trip context.
2. If `status` is `interrupt`, inspect `interrupt` for pending selections, gather a user decision, and send `/plan/resume/{thread_id}` with the indices.
3. Repeat resume calls until status becomes `complete` (final itinerary) or `no_plan`.

## Testing

```bash
source .venv/bin/activate
pytest
```

The test suite covers:
- Domain model validation (`tests/test_domain.py`)
- External service helpers (`tests/test_services.py`)
- LangGraph node behaviour and compilation (`tests/test_workflow_nodes.py`)
- API contract using a stubbed workflow bundle (`tests/test_api.py`)

## Development Guidelines

- Follow PEP 8 conventions and favour small, well-named helper functions.
- When notebook logic stabilises, extract shared code into `src/` modules with short docstrings.
- Keep generated data in `artifacts/` and shared datasets in `data/`.
- Mark long-running notebook cells with `@pytest.mark.slow` (see testing guidelines).

## Observability & Tracing

`ApiSettings` can enable LangSmith tracing if `LANGSMITH_API_KEY` is provided. Review `src/core/config.py` for configuration defaults and environment variable loading.

## Next Steps

- Extend RAG sources or agents as new travel domains emerge.
- Automate interrupt handling with UX surfaces (chat UI, dashboard).
- Integrate additional testing (e.g., `pytest --nbmake trip_planner.ipynb`).
