#!/usr/bin/env python3
"""Unit tests for the neofetch-style info card SVG."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_info_card import (  # noqa: E402
    InfoCardError,
    InfoLine,
    render_info_card,
    write_info_card,
)


def test_render_info_card_contains_keys() -> None:
    svg = render_info_card(static=True)
    assert "neofetch" in svg
    assert "Now" in svg
    assert "Stack" in svg
    assert "Highlights" in svg
    assert "fadeSlide" not in svg or "animation: none" in svg


def test_render_info_card_animated_has_keyframes() -> None:
    svg = render_info_card(static=False)
    assert "@keyframes fadeSlide" in svg
    assert "animation-delay" in svg


def test_render_escapes_html_in_values() -> None:
    lines = [InfoLine("Now", "<script>alert(1)</script>")]
    svg = render_info_card(lines, static=True)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_render_empty_lines_raises() -> None:
    with pytest.raises(InfoCardError, match="at least one"):
        render_info_card([], static=True)


def test_write_info_card(tmp_path: Path) -> None:
    out = tmp_path / "info-card.svg"
    write_info_card(out, static=True)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<svg")
    assert "User" in text
