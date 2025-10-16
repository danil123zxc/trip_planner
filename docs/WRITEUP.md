
# Trip Planner Project Write-up

## Overview
Trip Planner is an AI-assisted travel planning platform that coordinates a team of specialist agents through a LangGraph workflow. Starting from a structured trip request, the system performs targeted research, gathers candidates for each travel category, invites the user to make selections when needed, and ultimately synthesizes a curated day-by-day itinerary. The implementation evolved from the exploratory Jupyter notebook `trip_planner.ipynb` into a production-ready FastAPI service with a React frontend.

## Project Goals
- Deliver end-to-end automated trip planning that feels collaborative rather than opaque.
- Combine deterministic workflow orchestration with flexible LLM reasoning for research and synthesis.
- Support a human-in-the-loop review step so travellers can pick their favourite options before the itinerary is finalised.
- Keep the notebook prototype and the production modules in lockstep, ensuring the graph logic stays consistent across environments.
- Integrate multiple data sources (TripAdvisor, Amadeus, Reddit, and an internal vector store) to ground the agents' recommendations.

## How the System Works
### 1. Context & State Initialisation
User input is captured as a `Context` model that includes destination, dates, budget, travellers, and free-form notes. A `State` object threads through the workflow, accumulating agent outputs (budget, research candidates, selections, and the final plan) while retaining a running LangChain message history for traceability.

### 2. LangGraph Workflow
`src/workflows/planner.py` compiles a LangGraph `StateGraph` that mirrors the notebook logic:
- **Budget Estimate Node** – Uses an LLM with structured output to produce a category-level budget breakdown.
- **Research Plan Node** – Infers how many candidates each research agent should gather and geocodes the destination.
- **Parallel Research Agents** – Four React-style agents (lodging, activities, food, intercity transport) plus a recommendations agent run concurrently. They rely on the RAG pipeline and external tools to populate structured candidate lists.
- **Combined Human Review Node** – Pauses the graph (via `interrupt`) so the UI can ask the user to pick preferred options. When the workflow resumes, those selections are normalised back into the `State`.
- **Planner Node** – Calls the LLM with JSON-schema enforcement to generate the final multi-day itinerary using all previously gathered information.

### 3. Retrieval-Augmented Research
`src/pipelines/rag.py` configures embeddings, FAISS vector storage, and query routing. Agents combine this internal search with TripAdvisor, Amadeus flight data, a comprehensive internet search tool, and a Reddit insights tool. The blend ensures outputs stay grounded in up-to-date, credible sources.

### 4. API & Frontend Integration
`src/api/app.py` exposes FastAPI endpoints for starting and resuming planning sessions. `WorkflowBundle` in `src/api/workflow_service.py` owns the LangGraph instance, manages thread-specific contexts, and persists interrupts for later resumes. The React frontend streams progress, surfaces research candidates, and orchestrates the human review interactions.

## Architecture Summary
~~~
┌──────────────┐    ┌────────────────────┐    ┌──────────────────────┐
│ React Client │──▶ │ FastAPI Backend    │──▶ │ LangGraph Workflow   │
└──────────────┘    │  • Context storage │    │  • Budget agent      │
                    │  • Thread manager  │    │  • Research agents   │
                    └────────────────────┘    │  • Human review node │
                                              │  • Planner node      │
                                              └─────────┬────────────┘
                                                        │
                                              ┌─────────▼────────────┐
                                              │ External Services    │
                                              │  • RAG vector store  │
                                              │  • TripAdvisor API   │
                                              │  • Amadeus API       │
                                              │  • Reddit / Tavily   │
                                              └──────────────────────┘
~~~

## Key Challenges
- **Notebook ↔ Module Synchronisation:** Keeping exploratory notebook code and extracted modules aligned required disciplined development practices and frequent regression runs (`jupyter nbconvert --execute` and `pytest`).
- **LLM Tooling Nuances:** Ensuring each agent sent provider-compliant message payloads (especially with multimodal content requirements) was a recurring source of 400-series API errors.
- **Human Interrupt Handling:** Designing a combined interrupt that could gather selections across multiple categories while serialising/deserialising structured data back into Pydantic models required careful schema management.
- **External API Variability:** TripAdvisor and Amadeus rate limits, schema updates, and localisation issues demanded resilient tooling wrappers and graceful fallbacks.

## Results Achieved
- Reliable generation of budget-aware, multi-day itineraries tailored to user preferences.
- Real-time insight into agent reasoning through message history and structured outputs.
- Seamless human-in-the-loop experience that pauses and resumes the workflow without losing state.
- Modular architecture that lets new tools or research agents be added with minimal disruption.
- Automated validation paths (notebook execution plus the pytest suite) that keep the workflow healthy.

## Future Improvements
- **Richer Analytics:** Incorporate cost aggregation visuals, carbon footprint estimates, and safety scoring trends in the frontend.
- **Personalisation Layer:** Use traveller profiles, past trip feedback, or loyalty data to bias candidate selection.
- **Offline Caching:** Warm caches for popular destinations to reduce latency and reliance on rate-limited APIs.
- **Robust Testing:** Add integration tests that exercise full agent-to-tool loops with mocked external services, plus golden tests for notebook outputs.
- **Multi-Destination Support:** Extend the graph to handle multi-city itineraries with interleaved transport planning and optional branching.

## Conclusion
Trip Planner demonstrates how a LangGraph-driven, multi-agent system can transform a single trip request into a research-backed itinerary while keeping the traveller in control. The current platform offers a solid foundation for richer personalisation, deeper analytics, and broader travel services integration.
