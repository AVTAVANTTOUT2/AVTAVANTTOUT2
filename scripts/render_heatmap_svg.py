#!/usr/bin/env python3
"""Render ``data/contributions.json`` as an animated GitHub-style heatmap SVG.

Classic 53-week × 7-day calendar of rounded colored boxes, revealed once with
a diagonal slide-down (CSS keyframes on load, then freeze). Includes a
Less→More legend and a stats footer.

Run by ``.github/workflows/update-profile-art.yml`` after ``fetch_contributions.py``.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from config import PROMPT_HOST, STATIC

LOGGER = logging.getLogger("render_heatmap_svg")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_IN = ROOT / "data" / "contributions.json"
DEFAULT_OUT = ROOT / "contrib-heatmap.svg"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

CELL = int(os.environ.get("HEATMAP_CELL", "12"))
GAP = int(os.environ.get("HEATMAP_GAP", "3"))
STEP = CELL + GAP
PAD = 22
LEFT_LABEL_W = 30
TOP_LABEL_H = 20
TITLEBAR_H = 30

BG = "#0a0e14"
BG2 = "#0d1420"
FRAME = "#1f6feb"
MUTED = "#7d8590"
GREEN = "#39d353"
ACCENT = "#22d3ee"
GOLD = "#f2cc60"

COL_T = float(os.environ.get("HEATMAP_COL_T", "0.018"))
ROW_T = float(os.environ.get("HEATMAP_ROW_T", "0.045"))
CELL_DUR = float(os.environ.get("HEATMAP_CELL_DUR", "0.42"))

Cell = tuple[str, int, int] | None


class HeatmapError(Exception):
    """Raised when heatmap rendering fails."""


def level_for(count: int) -> int:
    """Map a raw contribution count to a palette level 0–5."""
    if count < 0:
        raise HeatmapError(f"Contribution count cannot be negative: {count}")
    if count == 0:
        return 0
    if count <= 5:
        return 1
    if count <= 15:
        return 2
    if count <= 30:
        return 3
    if count <= 50:
        return 4
    return 5


def build_grid(days: list[dict[str, Any]]) -> list[list[Cell]]:
    """Pack day records into week columns (Sunday-first)."""
    if not days:
        raise HeatmapError("Cannot build heatmap grid from empty days list")

    first = dt.date.fromisoformat(days[0]["date"])
    lead_pad = (first.weekday() + 1) % 7  # Sunday = 0
    grid: list[list[Cell]] = []
    col: list[Cell] = [None] * lead_pad

    for day in days:
        date = dt.date.fromisoformat(day["date"])
        weekday = (date.weekday() + 1) % 7
        while len(col) < weekday:
            col.append(None)
        count = int(day["count"])
        col.append((day["date"], count, level_for(count)))
        if len(col) == 7:
            grid.append(col)
            col = []

    if col:
        while len(col) < 7:
            col.append(None)
        grid.append(col)
    return grid


def render(data: dict[str, Any], *, static: bool = STATIC) -> str:
    """Render contribution ``data`` into a self-contained SVG string."""
    days = data.get("days")
    if not isinstance(days, list) or not days:
        raise HeatmapError(
            f"contributions payload for user {data.get('username', '?')} has no days"
        )

    grid = build_grid(days)
    n_cols = len(grid)
    art_w = n_cols * STEP
    art_h = 7 * STEP

    month_labels: list[tuple[int, str]] = []
    seen_months: set[tuple[int, int]] = set()
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue
            date = dt.date.fromisoformat(cell[0])
            key = (date.year, date.month)
            if key not in seen_months and date.day <= 7:
                seen_months.add(key)
                month_labels.append((ci, date.strftime("%b")))
            break

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    stats_h = 88
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + stats_h + PAD

    if static:
        css = ".c { opacity: 1; }"
    else:
        css = f"""
@keyframes cell {{
  0%   {{ opacity: 0; transform: translateY(-6px); }}
  100% {{ opacity: 1; transform: translateY(0); }}
}}
.c {{ opacity: 0; animation: cell {CELL_DUR:.2f}s cubic-bezier(.2,.8,.2,1) both; }}
""".strip()

    parts: list[str] = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
            f'viewBox="0 0 {canvas_w} {canvas_h}" '
            f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
        ),
        f"<style>{css}</style>",
        (
            "<defs>"
            '<linearGradient id="hbg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{BG2}"/>'
            f'<stop offset="1" stop-color="{BG}"/>'
            "</linearGradient></defs>"
        ),
        f'<rect width="{canvas_w}" height="{canvas_h}" rx="12" fill="url(#hbg)"/>',
        (
            f'<rect x="0.5" y="0.5" width="{canvas_w - 1}" height="{canvas_h - 1}" rx="12" '
            f'fill="none" stroke="{FRAME}" stroke-width="1" stroke-opacity="0.55"/>'
        ),
        (
            f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w}" y2="{TITLEBAR_H}" '
            f'stroke="{FRAME}" stroke-opacity="0.35"/>'
        ),
    ]

    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(
            f'<circle cx="{PAD + i * 16}" cy="{TITLEBAR_H / 2}" r="5" fill="{dotcol}"/>'
        )
    parts.append(
        f'<text x="{canvas_w / 2}" y="{TITLEBAR_H / 2 + 4}" fill="{MUTED}" font-size="12" '
        f'text-anchor="middle">{PROMPT_HOST}: ~/contributions --graph</text>'
    )

    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W

    for ci, label in month_labels:
        x = grid_left + ci * STEP
        parts.append(
            f'<text x="{x}" y="{TITLEBAR_H + 14}" fill="{MUTED}" font-size="10">{label}</text>'
        )

    for wi, wname in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = grid_top + wi * STEP + CELL * 0.78
        parts.append(
            f'<text x="{PAD}" y="{y:.1f}" fill="{MUTED}" font-size="9">{wname}</text>'
        )

    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            date_s, count, lvl = cell
            gy = grid_top + ri * STEP
            delay = ci * COL_T + ri * ROW_T
            plural = "s" if count != 1 else ""
            delay_attr = "" if static else f' style="animation-delay:{delay:.3f}s"'
            parts.append(
                f'<rect class="c" x="{gx}" y="{gy}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{PALETTE[lvl]}"{delay_attr}>'
                f"<title>{date_s}: {count} contribution{plural}</title></rect>"
            )

    leg_y = grid_top + art_h + 6
    leg_x = canvas_w - PAD - (len(PALETTE) * (CELL - 1) + 70)
    parts.append(
        f'<text x="{leg_x}" y="{leg_y + CELL * 0.8:.1f}" fill="{MUTED}" font-size="10" '
        f'text-anchor="end">Less</text>'
    )
    lx = leg_x + 8
    for color in PALETTE:
        parts.append(
            f'<rect x="{lx}" y="{leg_y}" width="{CELL - 1}" height="{CELL - 1}" '
            f'rx="2.2" fill="{color}"/>'
        )
        lx += CELL
    parts.append(
        f'<text x="{lx + 4}" y="{leg_y + CELL * 0.8:.1f}" fill="{MUTED}" font-size="10">More</text>'
    )

    sep_y = leg_y + CELL + 14
    parts.append(
        f'<line x1="0" y1="{sep_y}" x2="{canvas_w}" y2="{sep_y}" '
        f'stroke="{FRAME}" stroke-opacity="0.25"/>'
    )

    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    total = data["total_contributions"]
    best = data["best_day"]
    rng = data["range"]

    ly = sep_y + 24
    parts.append(
        f'<text x="{PAD}" y="{ly}" font-size="13" fill="{GREEN}">'
        f'<tspan font-weight="700">{total:,}</tspan>'
        f'<tspan fill="{MUTED}"> contributions in the last year</tspan></text>'
    )
    parts.append(
        f'<text x="{canvas_w - PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">'
        f'{rng["start"]} &#8594; {rng["end"]}</text>'
    )
    ly += 24
    parts.append(
        f'<text x="{PAD}" y="{ly}" font-size="13" fill="{MUTED}">current streak '
        f'<tspan fill="{ACCENT}" font-weight="700">{cs} days</tspan>'
        f'<tspan fill="{MUTED}">   &#183;   longest </tspan>'
        f'<tspan fill="{ACCENT}" font-weight="700">{ls} days</tspan></text>'
    )
    parts.append(
        f'<text x="{canvas_w - PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">'
        f'best day <tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> '
        f'on {best["date"]}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def write_heatmap(
    in_path: Path = DEFAULT_IN,
    out_path: Path = DEFAULT_OUT,
    *,
    static: bool = STATIC,
) -> Path:
    """Load JSON from ``in_path``, write SVG to ``out_path``, return ``out_path``."""
    if not in_path.is_file():
        raise HeatmapError(f"Contributions JSON not found: {in_path}")
    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HeatmapError(f"Invalid JSON in {in_path}: {exc}") from exc

    svg = render(data, static=static)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    LOGGER.info("Wrote %s (%d bytes)", out_path, len(svg))
    return out_path


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    in_path = Path(args[0]) if len(args) >= 1 else DEFAULT_IN
    out_path = Path(args[1]) if len(args) >= 2 else DEFAULT_OUT
    try:
        write_heatmap(in_path, out_path)
    except HeatmapError as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
