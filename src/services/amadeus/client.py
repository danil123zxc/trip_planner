from amadeus import Client
from amadeus.client.errors import ResponseError
import json
from src.core.config import ApiSettings


def create_amadeus_client(settings: ApiSettings, *, hostname: str = "test") -> Client:
    """Instantiate the Amadeus SDK client using project configuration."""

    client_id = settings.ensure("amadeus_api_key")
    client_secret = settings.ensure("amadeus_api_secret")
    return Client(client_id=client_id, client_secret=client_secret, hostname=hostname)

def _format_response_error(exc: ResponseError) -> str:
    """Return a human-friendly message for Amadeus errors."""

    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    raw_body = getattr(response, "body", None)

    details = None
    if raw_body:
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError:
            details = raw_body.strip()
        else:
            errors = parsed.get("errors") if isinstance(parsed, dict) else None
            if isinstance(errors, list):
                parts = []
                for item in errors:
                    if not isinstance(item, dict):
                        continue
                    code = item.get("code")
                    title = item.get("title")
                    detail = item.get("detail")
                    section = " ".join(filter(None, [code, title]))
                    if detail:
                        section = f"{section}: {detail}" if section else detail
                    if section:
                        parts.append(section)
                if parts:
                    details = "; ".join(parts)
            if details is None and isinstance(parsed, dict):
                for key in ("result", "message", "error"):
                    if key in parsed and isinstance(parsed[key], str):
                        details = parsed[key]
                        break
    prefix = f"HTTP {status}" if status else "Amadeus API error"
    if details:
        return f"{prefix}: {details}"
    return prefix