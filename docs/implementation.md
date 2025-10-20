# Feature Slice Implementation Guide

## Workflow-First Development
Trip Planner evolves from the notebook prototype. **Always update `trip_planner.ipynb` first**, execute it end-to-end, and only then port stable logic into `src/`. The notebook, extracted modules, and FastAPI surface must remain functionally identical.

Recommended loop:
1. Implement or refine the workflow inside the notebook.
2. Run `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb`.
3. Extract helper functions, prompts, and models into the corresponding modules.
4. Run `pytest -q` (or targeted suites) to confirm parity.
5. Sync documentation and examples in `examples/`.

## Repository Structure (High-Level)

```
trip_planner/
├── trip_planner.ipynb        # Canonical workflow definition
├── src/
│   ├── api/                  # FastAPI application surface
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   ├── response_builder.py
│   │   ├── schemas.py
│   │   └── workflow_service.py
│   ├── core/                 # Workflow building blocks
│   │   ├── builders.py       # LangGraph assembly & agent factories
│   │   ├── nodes.py          # Node implementations & prompts usage
│   │   ├── prompts.py        # Prompt templates shared with notebook
│   │   ├── post_processing.py# Structured output enforcement
│   │   ├── reducer.py        # State normalisation
│   │   ├── schemas.py        # Pydantic contracts
│   │   └── types.py
│   ├── pipelines/
│   │   └── rag.py            # Retrieval pipeline and embeddings config
│   └── services/             # External API clients & LangChain tools
│       ├── amadeus/
│       ├── geocoding/
│       ├── tavily_search/
│       ├── trip_advisor/
│       └── reddit/
├── tests/                    # Unit and integration suites
├── frontend/                 # React client for human-in-the-loop UX
└── docs/                     # Architecture and design references
```

## Implementing Changes by Slice

### Workflow Orchestration (`src/core/`)
- Update prompts and node logic in the notebook; copy changes into `src/core/prompts.py` and `src/core/nodes.py`.
- Use `create_pydantic_hook` to convert raw agent responses: extend `src/core/post_processing.py` when new schemas are introduced.
- When adding nodes or edges, mirror the graph definition in both notebook and `build_research_graph`.

### API Surface (`src/api/`)
- Validate new request/response fields in `src/api/schemas.py`.
- Update `_result_to_response` if additional payload sections are required.
- When introducing new endpoints, wire dependencies through `lifespan` and document them with descriptive docstrings (see `app.py`).

### Research Agents & Tools (`src/services/`)
- Add or update LangChain tools via service-specific `tools.py` modules.
- Ensure clients handle authentication from `ApiSettings` and expose typed responses in `schemas.py`.
- Register new tools inside `WorkflowBundle.__init__`, keeping the list of tools in sync with notebook experiments.

### Retrieval Pipeline (`src/pipelines/rag.py`)
- Adjust embeddings, vector store options, or reranking strategies here.
- When changing the exposed tool signature, update any agent prompts that rely on it.

### Frontend Integration (`frontend/`)
- `frontend/src/services/api.ts` mirrors API response models; update types when schemas change.
- `SelectionInterface.tsx` expects interrupt payloads grouped by category—keep naming consistent.

## Adding a New Agent (Example Workflow)
1. Prototype the agent prompt and tool usage in the notebook.
2. Define output schema in `src/core/schemas.py` (and notebook cell).
3. Extend `ResearchAgents` dataclass and `build_research_agents` to instantiate the agent.
4. Add a new node factory in `src/core/nodes.py` plus graph wiring in `build_research_graph`.
5. Update reducers and response builders to include the new agent output.
6. Regenerate API examples under `examples/` if payloads change.
7. Run notebook regression and targeted pytest modules (`tests/test_workflow_nodes.py`).

## Testing Strategy
- **Unit Tests** – Focus on reducers, post-processing hooks, and service clients (`tests/test_reducer.py`, `tests/test_services.py`).
- **Workflow Tests** – Validate node contracts and state transitions in `tests/test_workflow_nodes.py`.
- **API Contract Tests** – `tests/test_api.py` ensures endpoints stay backward compatible.
- **Notebook Regression** – Mandatory before merging workflow changes.
- **Frontend Smoke** – Regenerate TypeScript types or update mocks if response shapes change.

## Common Pitfalls & Mitigations
- **Notebook Drift** – Always diff notebook output after exporting logic; mismatches quickly lead to runtime errors.
- **Schema Changes** – When expanding models, update both Python Pydantic classes and TypeScript interfaces to avoid serialisation issues.
- **Tool Rate Limits** – Wrap external calls with retry/backoff logic in service clients and expose graceful fallbacks in agent prompts.
- **Thread Leaks** – Call `/plan/cleanup_threads` in non-production environments or configure a scheduler in production deployments.

## Command Reference
- Execute notebook: `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb`
- Run tests: `pytest -q`
- Run specific suite: `pytest tests/test_workflow_nodes.py -vv`
- Start API locally: `uvicorn src.api.app:app --reload`
- Launch frontend: `npm install && npm run dev --prefix frontend`

## Documentation Hygiene
- Update diagrams in `docs/` whenever workflow structure or service inventory changes.
- Refresh `examples/*.json` payloads after schema updates.
- Record notable architecture decisions in `docs/WRITEUP.md` or complementary ADRs.

Following this guide keeps the notebook, Python modules, and frontend aligned while preserving the feature slice intent behind the current architecture.
