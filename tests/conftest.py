"""Pytest configuration for the trip planner project."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so that import src works under pytest.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
