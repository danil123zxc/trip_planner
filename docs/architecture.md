# Trip Planner Architecture Guide

## System Overview
The Trip Planner runtime is a layered system that turns a structured request into a human-approved itinerary. At the heart of the system is a LangGraph workflow that orchestrates specialist research agents and a final planning LLM. The diagram below captures the major runtime components.

```
┌───────────────────────────────────────────────────────────────┐
│                       Trip Planner Stack                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    HTTP    ┌─────────────────────────────┐   │
│  │ React Client │ ─────────▶ │ FastAPI (`src/api/app.py`)  │   │
│  │  Selection   │ ◀───────── │ • Request validation        │   │
│  │   UI         │  JSON      │ • Thread lifecycle          │   │
│  └──────────────┘            │ • Sentry / CORS             │   │
│                               └──────────────┬──────────────┘   │
│                                              │ invokes          │
│                                              ▼                  │
│                               ┌─────────────────────────────┐   │
│                               │ WorkflowBundle              │   │
│                               │ `src/api/workflow_service`  │   │
│                               │ • LangGraph compilation     │   │
│                               │ • Agent/tool wiring         │   │
│                               │ • Thread registry           │   │
│                               └──────────────┬──────────────┘   │
│                                              │ runs             │
│                                              ▼                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ LangGraph Workflow (`src/core/builders.py`)               │ │
│  │ • Budget → Research Plan → Parallel Agents                │ │
│  │ • Combined Human Review interrupt                         │ │
│  │ • Final Planner                                           │ │
│  └───────────────────────┬──────────────────────────────────┘ │
│                          │ agent calls                        │
│                          ▼                                    │
│        ┌───────────────────────────────────────────────┐      │
│        │ Research Agents (`create_react_agent`)        │      │
│        │ • Lodging / Activities / Food / Transport     │      │
│        │ • Recommendations aggregator                  │      │
│        └───────────────┬───────────────┬───────────────┘      │
│                        │ tools         │                       │
│                        ▼               ▼                       │
│   ┌────────────────────────────┐   ┌────────────────────────┐  │
│   │ Retrieval Pipeline         │   │ External API Clients    │  │
│   │ `src/pipelines/rag.py`     │   │ `src/services/*`        │  │
│   │ • Vector search (`search`) │   │ • TripAdvisor / Amadeus │  │
│   │ • Reranking                │   │ • Tavily / Reddit       │  │
│   └────────────────────────────┘   │ • Geocoding             │  │
│                                     └────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## LangGraph Node Map

| Node | Source | Responsibility | Key Outputs |
| --- | --- | --- | --- |
| `budget_estimate` | `make_budget_estimate_node` | Structured budget breakdown using ChatXAI structured output. | `BudgetEstimate`, budget messages |
| `research_plan` | `make_research_plan_node` | Decide candidate counts, geocode destination, prime shared context. | `ResearchPlan`, updated coordinates |
| `research_lodging` | `make_lodging_node` | Query TripAdvisor + internal search for accommodations. | `LodgingAgentOutput` |
| `research_activities` | `make_activities_node` | Surface activities and points of interest. | `ActivitiesAgentOutput` |
| `research_food` | `make_food_node` | Gather dining options with budgets. | `FoodAgentOutput` |
| `research_intercity_transport` | `make_intercity_transport_node` | Identify flight/train/bus options via Amadeus tools. | `IntercityTransportAgentOutput` |
| `research_recommendations` | `make_recommendations_node` | Combine Reddit, Tavily, and vector search for additional tips. | `RecommendationsOutput` |
| `combined_human_review` | `make_combined_human_review_node` | Emit interrupt payload that the UI presents for user selections. | Interrupt contract with candidates |
| `planner` | `make_planner_node` | Produce the final multi-day itinerary from selections and prior research. | `FinalPlan` |

Each research node relies on a REACT agent bound to prompts in `src/core/prompts.py` and post-processed via `create_pydantic_hook` to guarantee schema compliance.

## Thread Lifecycle and Interrupt Handling
1. **Start** – `/plan/start` constructs a fresh thread (`thread_id`). The graph executes until it reaches an interrupt or finishes.
2. **Interrupt** – `combined_human_review` raises `langgraph.types.interrupt`. `WorkflowBundle` captures the partial state along with `config` metadata returned to the client.
3. **User Selection** – The frontend displays candidate lists; chosen IDs are posted back via `/plan/final_plan` (or `/plan/extra_research` for more options).
4. **Resume** – `WorkflowBundle.final_plan` restores stored state and resumes execution. Once the planner node completes, the thread produces a `FinalPlan`.
5. **Cleanup** – `/plan/cleanup_threads` removes threads whose last update is older than the configured TTL (default 60 minutes).

## Data Contracts
- **Requests** – `PlanRequest`, `ExtraResearchRequest`, `FinalPlanRequest` defined in `src/api/schemas.py` mirror notebook models.
- **State Models** – `Context`, `State`, and all candidate models live in `src/core/schemas.py`.
- **Responses** – `PlanningResponse` encapsulates status (`interrupt`, `complete`, `needs_follow_up`, `no_plan`), research artefacts, and final itineraries. `src/api/response_builder.py` assembles this shape.
- **Interrupt Payload** – Contains labelled candidate lists grouped by category and is consumed directly by `SelectionInterface.tsx`.

## Tooling & External Services
- **TripAdvisor** (`src/services/trip_advisor/*`): Search endpoints with rate-limit aware client wrappers and normalised response schemas.
- **Amadeus** (`src/services/amadeus/*`): Flight search support for the intercity transport agent.
- **Tavily Search** (`src/services/tavily_search/*`): General web search tool used by the recommendations agent.
- **Reddit Insights** (`src/services/reddit/*`): Community-sourced tips routed through the retrieval pipeline for grounding.
- **Geocoding** (`src/services/geocoding/geocoding.py`): Nominatim lookup executed during research planning.
- **Internal Vector Store** (`src/pipelines/rag.py`): FAISS-backed search that exposes `search_db` LangChain tool.

## Observability and Configuration
- **Sentry** – Optional error reporting initialised in `src/api/app.py` when `SENTRY_DSN` is set.
- **LangSmith Tracing** – Enabled via `ApiSettings.apply_langsmith_tracing()`.
- **Logging** – FastAPI endpoints annotate request lifecycle; agents log prompts and raw responses (at debug level).
- **Environment** – `.env` supplies API keys; `src/core/config.ApiSettings` validates presence and normalises case.

## Deployment Considerations
- **Containerisation** – `Dockerfile` + `docker-compose.yml` provide local orchestration with Postgres instance suitable for future persistence layers.
- **Thread Persistence** – Current implementation is in-memory (`InMemorySaver`). Production deployments should replace with a database-backed checkpoint.
- **Scaling** – FastAPI app can scale horizontally; ensure shared checkpoint storage and cache warming for retrieval pipelines.
- **Testing Gates** – CI should execute notebook regression (`jupyter nbconvert ...`) followed by `pytest`. Any divergence between notebook and modules must be reconciled before deployment.
