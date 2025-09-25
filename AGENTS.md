# Repository Guidelines

## Project Structure & Module Organization
The repository currently centers on `trip_planner.ipynb`, which captures the full discovery-to-output workflow. Store shared datasets under `data/` (create the folder if absent) and drop any generated maps, CSV exports, or model snapshots in `artifacts/` so they can be git-ignored and recreated. When notebook logic stabilizes, extract reusable helpers into `src/` modules that mirror notebook sections and document them with concise docstrings for quick reuse.

## Build, Test, and Development Commands
Work inside a dedicated virtual environment to keep dependencies reproducible:
- `python -m venv .venv` — create an isolated interpreter.
- `source .venv/bin/activate` (or `./.venv/Scripts/activate` on Windows) — activate it for the current shell.
- `pip install -r requirements.txt` — install the pinned packages; refresh the file with `pip freeze > requirements.txt` after dependency changes.
- `jupyter lab` — launch the interactive environment for exploratory edits.
- `jupyter nbconvert --execute --to notebook --inplace trip_planner.ipynb` — run the notebook headlessly to confirm all cells pass before committing.

## Coding Style & Naming Conventions
Notebook Python cells should follow PEP 8: four-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and descriptive markdown headings preceding major code blocks. Keep outputs trimmed to the smallest artifact needed and prefer in-notebook helper functions over long procedural cells.

## Testing Guidelines
Add unit tests for extracted modules under `tests/` using `pytest`. For notebook regressions, enable `pytest --nbmake trip_planner.ipynb` so each cell executes in CI; mark long-running cells with `@pytest.mark.slow` and guard them with skips. Document expected inputs and outputs near any data-loading cell so test fixtures can mirror them.

## Commit & Pull Request Guidelines
Write commit subjects in the imperative mood (`Add itinerary scoring helper`) and include a short body that lists notebook sections touched or data artifacts regenerated. Pull requests should link to the planning issue, include before-and-after screenshots of primary outputs, and call out any new dependencies or environment variables required. Request review once the notebook runs cleanly via `nbconvert` and all tests pass locally.

