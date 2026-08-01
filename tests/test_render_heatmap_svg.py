#!/usr/bin/env python3
"""Unit tests for heatmap level mapping, grid packing, and SVG render."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_heatmap_svg import (  # noqa: E402
    HeatmapError,
    build_grid,
    level_for,
    render,
    write_heatmap,
)


def test_level_for_boundaries() -> None:
    assert level_for(0) == 0
    assert level_for(1) == 1
    assert level_for(5) == 1
    assert level_for(6) == 2
    assert level_for(15) == 2
    assert level_for(16) == 3
    assert level_for(30) == 3
    assert level_for(31) == 4
    assert level_for(50) == 4
    assert level_for(51) == 5


def test_level_for_rejects_negative() -> None:
    with pytest.raises(HeatmapError, match="negative"):
        level_for(-1)


def test_build_grid_sunday_aligned() -> None:
    # 2026-01-04 is a Sunday.
    days = [
        {"date": "2026-01-04", "count": 1},
        {"date": "2026-01-05", "count": 2},
        {"date": "2026-01-06", "count": 0},
        {"date": "2026-01-07", "count": 8},
        {"date": "2026-01-08", "count": 0},
        {"date": "2026-01-09", "count": 0},
        {"date": "2026-01-10", "count": 40},
    ]
    grid = build_grid(days)
    assert len(grid) == 1
    assert grid[0][0] is not None and grid[0][0][0] == "2026-01-04"
    assert grid[0][6] is not None and grid[0][6][2] == 4


def test_build_grid_empty_raises() -> None:
    with pytest.raises(HeatmapError, match="empty days"):
        build_grid([])


def test_render_includes_palette_and_stats() -> None:
    data = {
        "username": "tester",
        "total_contributions": 42,
        "current_streak": {"length": 3, "start": "2026-01-01", "end": "2026-01-03"},
        "longest_streak": {"length": 5, "start": "2025-12-01", "end": "2025-12-05"},
        "best_day": {"date": "2026-01-02", "count": 20},
        "range": {"start": "2026-01-01", "end": "2026-01-03"},
        "days": [
            {"date": "2026-01-01", "count": 1},
            {"date": "2026-01-02", "count": 20},
            {"date": "2026-01-03", "count": 0},
        ],
    }
    svg = render(data, static=True)
    assert svg.startswith("<svg")
    assert "#39d353" in svg
    assert "42" in svg
    assert "Less" in svg and "More" in svg
    assert "animation-delay" not in svg


def test_render_animated_has_delays() -> None:
    data = {
        "username": "tester",
        "total_contributions": 1,
        "current_streak": {"length": 1, "start": "2026-01-04", "end": "2026-01-04"},
        "longest_streak": {"length": 1, "start": "2026-01-04", "end": "2026-01-04"},
        "best_day": {"date": "2026-01-04", "count": 1},
        "range": {"start": "2026-01-04", "end": "2026-01-04"},
        "days": [{"date": "2026-01-04", "count": 1}],
    }
    svg = render(data, static=False)
    assert "animation-delay" in svg
    assert "@keyframes cell" in svg


def test_write_heatmap_roundtrip(tmp_path: Path) -> None:
    payload = {
        "username": "tester",
        "total_contributions": 1,
        "current_streak": {"length": 1, "start": "2026-01-04", "end": "2026-01-04"},
        "longest_streak": {"length": 1, "start": "2026-01-04", "end": "2026-01-04"},
        "best_day": {"date": "2026-01-04", "count": 1},
        "range": {"start": "2026-01-04", "end": "2026-01-04"},
        "days": [{"date": "2026-01-04", "count": 1}],
    }
    src = tmp_path / "contributions.json"
    out = tmp_path / "contrib-heatmap.svg"
    src.write_text(json.dumps(payload), encoding="utf-8")
    write_heatmap(src, out, static=True)
    text = out.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "contribution" in text


def test_write_heatmap_missing_file(tmp_path: Path) -> None:
    with pytest.raises(HeatmapError, match="not found"):
        write_heatmap(tmp_path / "missing.json", tmp_path / "out.svg")
