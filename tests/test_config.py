#!/usr/bin/env python3
"""Unit tests for shared config helpers."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_env_bool_and_float(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATIC", "true")
    monkeypatch.setenv("GH_HTTP_TIMEOUT", "12.5")
    monkeypatch.setenv("GH_PROFILE_USER", "someone")
    import config

    importlib.reload(config)
    assert config.STATIC is True
    assert config.HTTP_TIMEOUT_SECONDS == 12.5
    assert config.USERNAME == "someone"
    # restore defaults for other modules importing config in-process
    monkeypatch.delenv("STATIC", raising=False)
    monkeypatch.delenv("GH_HTTP_TIMEOUT", raising=False)
    monkeypatch.delenv("GH_PROFILE_USER", raising=False)
    importlib.reload(config)


def test_env_float_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GH_HTTP_TIMEOUT", "nope")
    import config

    with pytest.raises(ValueError, match="GH_HTTP_TIMEOUT"):
        importlib.reload(config)
    monkeypatch.delenv("GH_HTTP_TIMEOUT", raising=False)
    importlib.reload(config)
