# Trip Planner Feature Slice Design

## Overview
Trip Planner coordinates a LangGraph-driven workflow that combines multiple research agents, retrieval tooling, and external services to produce a personalised itinerary. The end-to-end behaviour is prototyped in `trip_planner.ipynb` and mirrored in the Python modules under `src/`. This document describes the feature-oriented slices that make up the current implementation and how they collaborate at runtime.

## Canonical Workflow Sources
- `trip_planner.ipynb` – exploratory notebook that defines the reference LangGraph workflow, prompts, and models.
- `src/core/` – extracted workflow primitives (schemas, nodes, builders, reducers, prompts, post-processing helpers).
- `src/api/` – FastAPI surface that exposes the workflow and owns thread lifecycle management.
- `src/pipelines/rag.py` – retrieval pipeline configuration used by the research agents.
- `src/services/` – API clients and LangChain tools for TripAdvisor, Amadeus, Tavily search, Reddit, and geocoding.
- `tests/` – unit and integration tests that exercise reducers, post-processing hooks, workflow nodes, and service integrations.

## Feature-Oriented Slices

| Slice | Primary Role | Key Modules | Upstream Inputs | Downstream Outputs |
| --- | --- | --- | --- | --- |
| **Workflow Orchestration** | Compile and run the LangGraph state machine, manage state transitions, interrupts, and final synthesis. | `trip_planner.ipynb`, `src/core/builders.py`, `src/core/nodes.py`, `src/core/reducer.py`, `src/core/post_processing.py` | Trip context (`Context`), traveller metadata, external tool handles | `State` mutations, agent tasks, final itinerary |
| **Domain & Schemas** | Declare strongly-typed models shared across notebook, API, and frontend. | `src/core/schemas.py`, `src/core/types.py` | User input, agent outputs | JSON responses, validation contracts |
| **API Surface** | Provide REST endpoints, request validation, response shaping, and thread persistence. | `src/api/app.py`, `src/api/schemas.py`, `src/api/response_builder.py`, `src/api/workflow_service.py`, `src/api/dependencies.py` | HTTP payloads, session metadata | `PlanningResponse`, `FinalPlan`, thread config |
| **Research Agents** | Execute specialist research (lodging, activities, food, intercity transport, recommendations). | Agent factories in `src/core/builders.py`, node helpers in `src/core/nodes.py` | Prompts, research plan, LangChain tools | Candidate collections (`CandidateLodging`, `CandidateActivity`, etc.) |
| **Retrieval & Knowledge** | Supply RAG-powered context and internal research corpus search. | `src/pipelines/rag.py`, `src/pipelines/schemas.py` | Queries from agents, embeddings config | Reranked documents and tool outputs (`search_db` tool) |
| **External Services & Tools** | Wrap TripAdvisor, Amadeus, Reddit, Tavily, and geocoding APIs as LangChain tools with shared logging and error handling. | `src/services/*` | Authentication from `ApiSettings`, queries from agents | Structured search results (flights, accommodations, insights) |
| **Frontend Integration** | Offer user interface for trip planning, interrupt handling, and final itinerary visualisation. | `frontend/src/` (notably `components/SelectionInterface.tsx`, `services/api.ts`) | API responses | User selections, follow-up requests |
| **Configuration & Observability** | Manage environment settings, Sentry integration, and LangSmith tracing. | `src/core/config.py`, `.env`, FastAPI `lifespan` dependency | Process environment | Configured clients, tracing hooks |

Each slice is designed to be independently testable and to communicate through well-defined Pydantic models. The notebook remains the single source of truth; extracted modules must stay functionally identical.

## Data Flow Walkthrough
1. **Request Intake** – The frontend sends a `PlanRequest` to `/plan/start`. FastAPI validates the payload and logs request metadata.
2. **Bundle Setup** – `WorkflowBundle` ensures all required API keys are present, instantiates the ChatXAI model, constructs the retrieval pipeline, and prepares LangChain tools.
3. **Graph Execution** – `build_research_graph` compiles the LangGraph `StateGraph` with budget, research, human review, and planner nodes.
4. **Research Phase** – The research plan node routes work to parallel REACT agents. Each agent calls TripAdvisor, Tavily, Reddit, and/or Amadeus tools with structured prompts defined in `src/core/prompts.py`.
5. **Interrupt Handling** – `combined_human_review` emits an interrupt when user selections are required. `WorkflowBundle` captures thread state and returns an interrupt payload to the client.
6. **Resume & Finalise** – The client posts selections to `/plan/final_plan`, `WorkflowBundle` restores the thread state, and the planner node produces a `FinalPlan`.
7. **Extra Research** – If a user requests more options, `/plan/extra_research` executes additional agent passes with the updated research plan.

## Cross-Cutting Concerns
- **State Management** – `src/core/reducer.py` normalises agent outputs into the `State` object, keeping message history for transparency.
- **Structured Outputs** – `src/core/post_processing.py` enforces JSON-schema compliance from LLM agents, ensuring downstream validators receive clean data.
- **Prompts** – `src/core/prompts.py` contains templated prompts tuned in the notebook, kept consistent with extracted modules.
- **Logging & Monitoring** – FastAPI endpoints log at info and debug levels; Sentry can be enabled via `SENTRY_DSN`; LangSmith tracing is activated through `ApiSettings`.

## Testing and Validation
- **Notebook Regression** – `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb`
- **Unit Tests** – `pytest -k "reducer or post_processing"` for core reducers and normalisers.
- **Workflow Tests** – `tests/test_workflow_nodes.py` exercises LangGraph nodes with fixtures.
- **Service Tests** – `tests/test_services.py` validates tool construction and API clients with mocked dependencies.
- **API Tests** – `tests/test_api.py` covers endpoint contracts using FastAPI’s test client.

Always execute both notebook and pytest suites after changing prompts, schemas, or workflow logic.

## Future Enhancements
- Extend the recommendations agent with dynamic tool selection based on traveller interests.
- Add caching layers around external APIs to reduce latency and rate-limiting risk.
- Expand contract tests for interrupt payloads to protect the frontend’s selection interface.
- Evaluate batching strategies for retrieval queries when multiple agents target the same destination context.
