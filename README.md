   # Trip Planner

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](requirements.txt) [![FastAPI](https://img.shields.io/badge/FastAPI-ready-teal.svg)](src/api/app.py) [![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Trip Planner is an agentic travel-planning platform that orchestrates a LangGraph workflow to research, price, and assemble day-by-day itineraries. The project originates in the explorative `trip_planner.ipynb` notebook and promotes a notebook-first workflow where production modules mirror the canonical notebook implementation.

## What the Project Does

- Coordinates specialised agents (budget, research planning, lodging, activities, food, transport, and final planner) through a LangGraph `StateGraph`.
- Executes research phases in parallel, surfaces human-in-the-loop interruptions, and resumes once selections are supplied.
- Combines external services (TripAdvisor, Amadeus, Tavily Search, Reddit, geocoding) with a retrieval-augmented generation (RAG) pipeline for up-to-date travel intelligence.
- Exposes the planning workflow through a FastAPI service and a React/TypeScript frontend for interactive trip creation.

### Workflow Highlights

- **Notebook as source of truth:** All behaviour is first implemented and validated in `trip_planner.ipynb` before extraction into modules under `src/`.
- **Structured state management:** Shared `State` and `Context` models (see `src/core/domain.py`) keep agent outputs and user context aligned.
- **Human decision points:** Interrupt nodes request user selections for lodging, dining, activities, and transport options before the planner agent finalises the itinerary.

`trip_planner_diagram.png`

## Why the Project Is Useful

- Produces complete, budget-aware itineraries with minimal manual research.
- Surfaces multiple vetted options per travel category, enabling informed choices.
- Keeps data fresh via live search tools and a reusable RAG pipeline (`src/pipelines/rag.py`).
- Offers clear extension points for new agents, tools, or data sources.
- Supports both programmatic access (FastAPI) and an interactive frontend experience.

## How to Get Started

### Prerequisites

- Python 3.12 or later
- Node.js 16 or later
- An `.env` populated from `.env.example` with relevant API keys (OpenAI, Tavily, Reddit, TripAdvisor, Amadeus, etc.)

### Clone and Configure

```bash
git clone <repository-url>
cd trip_planner
cp .env.example .env  # update with your credentials
```

### Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The React client renders workflow progress, interrupts, and final trip outputs in real time.

### Notebook Workflow

Run the canonical notebook to validate changes and keep behaviour in sync:

```bash
jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb
```

### Test Suite

```bash
pytest                              # unit and integration tests
pytest --nbmake trip_planner.ipynb  # notebook regression
```

### Try the Planning API

Start a session with the FastAPI backend running:

```bash
curl -X POST http://localhost:8000/plan/start \
  -H "Content-Type: application/json" \
  -d '{
        "context": {
          "destination": "Tokyo",
          "destination_country": "Japan",
          "date_from": "2025-10-01",
          "date_to": "2025-10-05",
          "budget": 2500,
          "currency": "USD",
          "group_type": "couple",
          "travellers": [
            {"name": "Jordan", "date_of_birth": "1992-04-12"},
            {"name": "Riley", "date_of_birth": "1991-08-03"}
          ],
          "trip_purpose": "cultural immersion",
          "current_location": "San Francisco"
        }
      }'
```

Responses return `status="interrupt"` when human selections are required and `status="complete"` with a `final_plan` once the itinerary is ready.

## Where Users Can Get Help

- Review the narrative and architecture context in `docs/WRITEUP.md`.
- Explore workflow and agent guidance in `AGENTS.md` and `docs/feature-slice-design.md`.
- Check `src/api/schemas.py` and `src/core/domain.py` for request/response contracts.
- Open a GitHub issue for bugs, questions, or integration discussions.

## Who Maintains and Contributes

- Maintained by [@danil123zxc](https://github.com/danil123zxc) 
- Contributions follow the notebook-first process: prototype in `trip_planner.ipynb`, reflect stable logic in `src/`, and keep both implementations synchronised.
- Before submitting a pull request:
  - Execute the notebook via `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb`.
  - Run `pytest` (and `pytest --nbmake trip_planner.ipynb` when notebook changes occur).
  - Update relevant docs under `docs/` if behaviour changes.

## Project Structure

| Path | Description |
| --- | --- |
| `trip_planner.ipynb` | Canonical LangGraph workflow and development reference |
| `src/core/domain.py` | Pydantic models for context, state, agent outputs, and final plan |
| `src/workflows/planner.py` | LangGraph graph construction, node wiring, and interrupt handling |
| `src/pipelines/rag.py` | Retrieval pipeline feeding research agents |
| `src/api/` | FastAPI surface including schemas, dependencies, and response adapters |
| `src/services/` | Integrations for TripAdvisor, Amadeus, Tavily Search, Reddit, and geocoding |
| `frontend/` | React/TypeScript client for human-in-the-loop interactions |
| `tests/` | Unit, service, workflow, and notebook regression tests |
| `docs/` | Architecture notes, feature slice design, and project write-up |

## Architecture Snapshot

- **Graph Orchestration:** `StateGraph` nodes mirror the notebook’s structure with conditional edges for route selection and interrupts for user choices.
- **Agent Suite:** Budget estimation, research planning, lodging, activities, dining, transport, and final planner agents each consume structured prompts and validated schemas.
- **RAG Foundation:** `RetrievalPipeline` ingests external search and forum data into a FAISS index, exposing shared tools (`search_db`, TripAdvisor, Amadeus, Reddit) to agent nodes.
- **API Layer:** `src/api/app.py` exposes endpoints for starting plans, resuming after selections, and requesting extra research, with responses adapted via `src/api/response_builder.py`.

For deeper dives, start with `trip_planner.ipynb` and cross-reference the mirrored Python modules under `src/`.

