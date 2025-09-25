"""Shared type aliases used across the extracted modules."""
from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

NonNegMoney = Annotated[float, Field(ge=0)]
Lat = Annotated[float, Field(ge=-90, le=90)]
Lon = Annotated[float, Field(ge=-180, le=180)]
Rating = Annotated[float, Field(ge=0, le=5)]
ISO4217 = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
HttpURLStr = Annotated[
    str,
    StringConstraints(
        pattern=r"^https?://[\w\-./%?#=&]+$",
        strip_whitespace=True,
    ),
]
TimeHHMM = Annotated[
    str,
    StringConstraints(
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        strip_whitespace=True,
    ),
]
