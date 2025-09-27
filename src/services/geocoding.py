"""Small helpers for using the public Nominatim geocoding service."""
from __future__ import annotations

from typing import Optional

import requests


def get_coordinates_nominatim(location: str, *, user_agent: str = "TripPlanner/1.0") -> Optional[str]:
    """Return a `lat,lon` string for the requested location or ``None``."""
    
    if not location:
        return None

    try:
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        headers = {"User-Agent": user_agent}
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            first = data[0]
            return f"{first['lat']},{first['lon']}"
        return None
    except Exception:
        return None
