"""Report branding — company logo and metadata for production HTML exports."""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


def _default_logo_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "assets" / "logo.svg"


@lru_cache(maxsize=1)
def load_logo_data_uri() -> str:
    """Return logo as a data URI for embedding in HTML reports."""
    settings = get_settings()
    logo_path = Path(settings.report_logo_path) if settings.report_logo_path else _default_logo_path()
    if not logo_path.is_file():
        return ""

    raw = logo_path.read_bytes()
    media = "image/svg+xml" if logo_path.suffix.lower() == ".svg" else "image/png"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{media};base64,{encoded}"


def report_branding_context() -> dict[str, str]:
    settings = get_settings()
    return {
        "company_name": settings.report_company_name,
        "company_tagline": settings.report_company_tagline,
        "company_website": settings.report_company_website,
        "logo_data_uri": load_logo_data_uri(),
    }
