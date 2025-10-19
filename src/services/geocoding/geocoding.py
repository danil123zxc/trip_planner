"""Small helpers for using the public Nominatim geocoding service."""
from __future__ import annotations

from typing import Optional

import requests
import httpx
import asyncio


async def get_coordinates_nominatim(
    location: str,
    *,
    user_agent: str = "TripPlanner/1.0",
    timeout: float = 10.0,
) -> Optional[str]:
    """Return a `lat,lon` string for the requested location or ``None``."""

    if not location:
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": user_agent}) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": location, "format": "json", "limit": 1, "addressdetails": 1},
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return None

    if not data:
        return None

    first = data[0]
    return f"{first['lat']},{first['lon']}"