#!/usr/bin/env python3
"""Hand-author a neofetch-style info card SVG that fades in line by line.

Content lives here on purpose: the contribution heatmap already covers GitHub
stats. The card tells the story numbers cannot.

Set ``STATIC=1`` to emit a frozen frame for local Quick Look previews.

Usage:
    python scripts/make_info_card.py [info-card.svg]
"""
from __future__ import annotations

import html
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from config import (
    DISPLAY_NAME,
    INFO_HIGHLIGHTS,
    INFO_LOCATION,
    INFO_PREV,
    INFO_ROLE,
    INFO_STACK,
    INFO_UPTIME,
    PROMPT_HOST,
    STATIC,
    USERNAME,
)

LOGGER = logging.getLogger("make_info_card")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_OUT = ROOT / "info-card.svg"

CANVAS_W = int(os.environ.get("INFO_CARD_WIDTH", "980"))
CANVAS_H = int(os.environ.get("INFO_CARD_HEIGHT", "820"))
PAD = 28
TITLEBAR_H = 30

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
MUTED = "#7d8590"
TEXT = "#e6edf3"
KEY_COLOR = "#79c0ff"
VALUE_COLOR = "#c9d1d9"
ACCENT = "#3fb950"
TITLE = "#ffa657"

LINE_DUR = float(os.environ.get("INFO_LINE_DUR", "0.35"))
LINE_STAGGER = float(os.environ.get("INFO_LINE_STAGGER", "0.12"))


@dataclass(frozen=True)
class InfoLine:
    """One neofetch key/value row."""

    key: str
    value: str
    key_color: str = KEY_COLOR
    value_color: str = VALUE_COLOR


class InfoCardError(Exception):
    """Raised when info-card generation fails."""


def default_lines() -> list[InfoLine]:
    """Return the default neofetch-style content rows."""
    return [
        InfoLine("User", f"{DISPLAY_NAME} ({USERNAME})", TITLE, TEXT),
        InfoLine("Now", INFO_ROLE, KEY_COLOR, VALUE_COLOR),
        InfoLine("Prev", INFO_PREV, KEY_COLOR, VALUE_COLOR),
        InfoLine("Stack", INFO_STACK, ACCENT, VALUE_COLOR),
        InfoLine("Highlights", INFO_HIGHLIGHTS, KEY_COLOR, VALUE_COLOR),
        InfoLine("Location", INFO_LOCATION, KEY_COLOR, VALUE_COLOR),
        InfoLine("Uptime", INFO_UPTIME, KEY_COLOR, VALUE_COLOR),
        InfoLine("Shell", "zsh + curiosity", KEY_COLOR, VALUE_COLOR),
        InfoLine("Editor", "neovim / Cursor", KEY_COLOR, VALUE_COLOR),
        InfoLine("Theme", "terminal-green-on-void", KEY_COLOR, VALUE_COLOR),
    ]


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def render_info_card(
    lines: list[InfoLine] | None = None,
    *,
    static: bool = STATIC,
) -> str:
    """Render a neofetch-style panel as a self-contained SVG string."""
    rows = list(lines) if lines is not None else default_lines()
    if not rows:
        raise InfoCardError("Info card requires at least one content line")

    css = (
        "@keyframes fadeSlide {"
        "  0%   { opacity: 0; transform: translateX(-10px); }"
        "  100% { opacity: 1; transform: translateX(0); }"
        "}"
        f".line {{ opacity: 0; animation: fadeSlide {LINE_DUR:.2f}s "
        "cubic-bezier(.2,.8,.2,1) both; }"
        ".static .line { opacity: 1; animation: none; }"
    )

    parts: list[str] = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
            f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
            f'Menlo, Consolas, monospace" class="{"static" if static else "live"}">'
        ),
        f"<style>{css}</style>",
        (
            "<defs>"
            '<linearGradient id="ibg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{BG2}"/>'
            f'<stop offset="1" stop-color="{BG}"/>'
            "</linearGradient></defs>"
        ),
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#ibg)"/>',
        (
            f'<rect x="0.5" y="0.5" width="{CANVAS_W - 1}" height="{CANVAS_H - 1}" rx="12" '
            f'fill="none" stroke="{FRAME}" stroke-width="1"/>'
        ),
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>',
    ]

    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(
            f'<circle cx="{PAD + i * 16}" cy="{TITLEBAR_H / 2}" r="5" fill="{dotcol}"/>'
        )
    parts.append(
        f'<text x="{CANVAS_W / 2}" y="{TITLEBAR_H / 2 + 4}" fill="{MUTED}" font-size="12" '
        f'text-anchor="middle">{_escape(PROMPT_HOST)}: ~$ neofetch</text>'
    )

    # Banner block — neofetch traditionally shows a logo; we keep a compact ASCII
    # header so the card stays self-contained beside the portrait.
    banner_y = TITLEBAR_H + 48
    parts.append(
        f'<text x="{PAD}" y="{banner_y}" fill="{TITLE}" font-size="22" font-weight="700" '
        f'class="line" style="animation-delay:0s">{_escape(DISPLAY_NAME)}</text>'
    )
    parts.append(
        f'<text x="{PAD}" y="{banner_y + 28}" fill="{MUTED}" font-size="13" class="line" '
        f'style="animation-delay:{LINE_STAGGER:.3f}s">'
        f'{_escape(PROMPT_HOST)} — {_escape(USERNAME)}</text>'
    )
    parts.append(
        f'<line x1="{PAD}" y1="{banner_y + 44}" x2="{CANVAS_W - PAD}" y2="{banner_y + 44}" '
        f'stroke="{FRAME}" stroke-opacity="0.8"/>'
    )

    key_width = 118
    y = banner_y + 78
    line_gap = 36
    for index, row in enumerate(rows):
        delay = (index + 2) * LINE_STAGGER
        parts.append(
            f'<text x="{PAD}" y="{y}" font-size="15" class="line" '
            f'style="animation-delay:{delay:.3f}s">'
            f'<tspan fill="{row.key_color}" font-weight="700">{_escape(row.key)}</tspan>'
            f'<tspan fill="{MUTED}">: </tspan>'
            f'<tspan fill="{row.value_color}" dx="{key_width - len(row.key) * 8}">'
            f"{_escape(row.value)}</tspan></text>"
        )
        y += line_gap

    # Color swatches — classic neofetch palette strip.
    swatch_y = min(y + 24, CANVAS_H - PAD - 18)
    swatches = [
        "#ff5f56",
        "#ffbd2e",
        "#27c93f",
        "#79c0ff",
        "#d2a8ff",
        "#ffa657",
        "#e6edf3",
        "#7d8590",
    ]
    sx = PAD
    delay = (len(rows) + 2) * LINE_STAGGER
    for color in swatches:
        parts.append(
            f'<rect class="line" x="{sx}" y="{swatch_y}" width="28" height="14" rx="3" '
            f'fill="{color}" style="animation-delay:{delay:.3f}s"/>'
        )
        sx += 34

    footer_y = swatch_y + 36
    if footer_y < CANVAS_H - 16:
        parts.append(
            f'<text x="{PAD}" y="{footer_y}" fill="{MUTED}" font-size="12" class="line" '
            f'style="animation-delay:{(len(rows) + 3) * LINE_STAGGER:.3f}s">'
            f"{_escape(PROMPT_HOST)}:~$ echo ready</text>"
        )

    parts.append("</svg>")
    return "".join(parts)


def write_info_card(out: Path, *, static: bool = STATIC) -> Path:
    """Write the info card SVG to ``out`` and return the path."""
    svg = render_info_card(static=static)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    LOGGER.info("Wrote %s (%d bytes)", out, len(svg))
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    out = Path(args[0]) if len(args) >= 1 else DEFAULT_OUT
    try:
        write_info_card(out)
    except InfoCardError as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
