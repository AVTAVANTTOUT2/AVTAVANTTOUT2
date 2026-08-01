#!/usr/bin/env python3
"""Shared configuration for profile-art generators.

Every public knobs is overridable via environment variables so the same
scripts work for any GitHub username without editing source.
"""
from __future__ import annotations

import os
from typing import Final


def _env(name: str, default: str) -> str:
    """Return stripped env value or default when unset/blank."""
    value = os.environ.get(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped if stripped else default


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment flag (1/true/yes/on)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """Parse a float environment value with fallback."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name}={raw!r} is not a float") from exc


USERNAME: Final[str] = _env("GH_PROFILE_USER", "AVIVASHISHTA29")
DISPLAY_NAME: Final[str] = _env("GH_PROFILE_DISPLAY_NAME", "Avi Vashishta")
PROMPT_HOST: Final[str] = _env("GH_PROFILE_PROMPT", "avi@github")
HTTP_TIMEOUT_SECONDS: Final[float] = _env_float("GH_HTTP_TIMEOUT", 30.0)
HTTP_USER_AGENT: Final[str] = _env(
    "GH_HTTP_USER_AGENT",
    "profile-readme-bot/1.0 (+https://github.com/AVIVASHISHTA29/AVIVASHISHTA29)",
)
STATIC: Final[bool] = _env_bool("STATIC", False)

# Info-card content (neofetch-style story lines).
INFO_ROLE: Final[str] = _env(
    "GH_INFO_ROLE",
    "Fullstack Developer · AI Builder · Instructor",
)
INFO_PREV: Final[str] = _env(
    "GH_INFO_PREV",
    "Shipped products, taught builders, open-sourced tooling",
)
INFO_STACK: Final[str] = _env(
    "GH_INFO_STACK",
    "TypeScript · Python · React · Node · AI/LLM",
)
INFO_HIGHLIGHTS: Final[str] = _env(
    "GH_INFO_HIGHLIGHTS",
    "Animated SVG profile · Self-hosted art · No third-party stats",
)
INFO_LOCATION: Final[str] = _env("GH_INFO_LOCATION", "Building on the internet")
INFO_UPTIME: Final[str] = _env("GH_INFO_UPTIME", "always shipping")
