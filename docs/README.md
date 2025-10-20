# Trip Planner Documentation Index

## Overview
This directory captures the architectural knowledge for the Trip Planner stack. Every document is synchronised with the production code under `src/` and the canonical workflow defined in `trip_planner.ipynb`. Use this index to navigate the available references and ensure updates stay aligned with the current implementation.

## Document Map

| Document | Purpose | When to Read |
| --- | --- | --- |
| [`design.md`](./design.md) | High-level feature slice overview, responsibilities, and data flow between major components. | Planning new features, onboarding to the codebase, aligning cross-team work. |
| [`architecture.md`](./architecture.md) | Deep dive into runtime architecture: LangGraph nodes, thread lifecycle, external services, observability. | Investigating workflow behaviour, debugging thread issues, explaining system internals. |
| [`implementation.md`](./implementation.md) | Practical guide for implementing changes while keeping notebook and modules in sync. | Day-to-day development, adding new agents, adjusting prompts or services. |
| [`diagram.txt`](./diagram.txt) | Text-only architecture diagram emphasising data flow and component boundaries. | Quick reference during reviews, presentations, or when visual tooling is unavailable. |
| [`WRITEUP.md`](./WRITEUP.md) | Narrative project summary, challenges, and future roadmap. | Context for stakeholders, retrospectives, and roadmap updates. |

## Keeping Documentation Current
- Mirror any changes made in `trip_planner.ipynb`, `src/`, or the frontend back into these notes.
- Update diagrams and example payloads alongside schema or workflow changes.
- Reference concrete modules and functions—avoid speculative future structures.
- Run notebook and pytest suites before publishing documentation updates to confirm accuracy.

## Related Resources
- **Examples**: `examples/*.json` demonstrate real API payloads.
- **Frontend**: `frontend/` contains the human-in-the-loop UI that consumes the documented contracts.
- **System Diagram**: `trip_planner_diagram.png` offers a visual complement to the ASCII diagram.

Maintaining these documents alongside the codebase ensures contributors share a single, accurate view of how the Trip Planner system works today.
