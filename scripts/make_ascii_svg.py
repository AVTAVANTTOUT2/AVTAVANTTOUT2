#!/usr/bin/env python3
"""Convert a prepped portrait into a self-typing monochrome ASCII SVG.

Each row is revealed with a left-to-right SMIL clip wipe and a block cursor
riding the wipe edge, staggered top → bottom. The portrait prints once and
freezes (no loop). GitHub renders the animation inside ``<img>``-embedded SVGs.

Usage:
    python scripts/make_ascii_svg.py [source-prepped.png] [avi-ascii.svg]
"""
from __future__ import annotations

import html
import logging
import os
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

from config import DISPLAY_NAME, PROMPT_HOST, STATIC

LOGGER = logging.getLogger("make_ascii_svg")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SRC = ROOT / "source-prepped.png"
DEFAULT_OUT = ROOT / "avi-ascii.svg"

COLS = int(os.environ.get("ASCII_COLS", "100"))
ROWS = int(os.environ.get("ASCII_ROWS", "53"))
CELL_W = int(os.environ.get("ASCII_CELL_W", "8"))
CELL_H = int(os.environ.get("ASCII_CELL_H", "15"))
RAMP = os.environ.get("ASCII_RAMP", " .`:-=+*cs#%@")

CONTRAST = float(os.environ.get("ASCII_CONTRAST", "1.05"))
BRIGHTNESS = float(os.environ.get("ASCII_BRIGHTNESS", "1.0"))
GAMMA = float(os.environ.get("ASCII_GAMMA", "1.18"))
SHARPEN = os.environ.get("ASCII_SHARPEN", "").strip().lower() in {"1", "true", "yes"}
WHITE_FLOOR = float(os.environ.get("ASCII_WHITE_FLOOR", "0.80"))

PAD = 20
TITLEBAR_H = 30
STATUS_H = 30
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"
CURSOR = "#c9d1d9"

ROW_DUR = float(os.environ.get("ASCII_ROW_DUR", "0.11"))
STAGGER = float(os.environ.get("ASCII_STAGGER", "0.11"))


class AsciiSvgError(Exception):
    """Raised when ASCII SVG generation fails."""


def luminance_to_glyph(lum: float) -> str:
    """Map a gamma-adjusted luminance in ``[0, 1]`` to an ASCII glyph."""
    if lum >= WHITE_FLOOR:
        return " "
    idx = int((1.0 - lum) * (len(RAMP) - 1) + 0.5)
    idx = max(0, min(len(RAMP) - 1, idx))
    return RAMP[idx]


def sample_rows(src: Path) -> list[str]:
    """Downsample ``src`` to a ``COLS×ROWS`` character grid."""
    if not src.is_file():
        raise AsciiSvgError(f"Prepped portrait not found: {src}")
    try:
        im = Image.open(src).convert("L")
    except OSError as exc:
        raise AsciiSvgError(f"Unable to open prepped portrait {src}: {exc}") from exc

    if SHARPEN:
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=140, threshold=2))
    im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    im = im.resize((COLS, ROWS), Image.Resampling.LANCZOS)
    pixels = im.load()
    if pixels is None:
        raise AsciiSvgError(f"Pillow returned empty pixel access for {src}")

    rows: list[str] = []
    for y in range(ROWS):
        chars: list[str] = []
        for x in range(COLS):
            lum = pow(pixels[x, y] / 255.0, GAMMA)
            chars.append(luminance_to_glyph(lum))
        rows.append("".join(chars))
    return rows


def render_ascii_svg(rows: list[str], *, static: bool = STATIC) -> str:
    """Render ASCII ``rows`` into a self-contained animated SVG document."""
    if len(rows) != ROWS:
        raise AsciiSvgError(f"Expected {ROWS} rows, got {len(rows)}")
    for i, line in enumerate(rows):
        if len(line) != COLS:
            raise AsciiSvgError(f"Row {i} has length {len(line)}, expected {COLS}")

    art_top = TITLEBAR_H + PAD * 0.35
    parts: list[str] = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
            f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
            f'Menlo, Consolas, monospace">'
        ),
        (
            "<defs>"
            '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{BG2}"/>'
            f'<stop offset="1" stop-color="{BG}"/>'
            "</linearGradient></defs>"
        ),
        f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>',
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
        f'<text x="{CANVAS_W / 2}" y="{TITLEBAR_H / 2 + 4}" fill="{TITLE_TEXT}" '
        f'font-size="12" text-anchor="middle">{PROMPT_HOST}: ~$ ./portrait.sh</text>'
    )

    font_size = CELL_H * 0.86
    for ry, line in enumerate(rows):
        y = art_top + ry * CELL_H + CELL_H * 0.74
        row_y = art_top + ry * CELL_H
        delay = ry * STAGGER
        safe = html.escape(line)
        text = (
            f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" '
            f'font-size="{font_size:.1f}" textLength="{ART_W}" lengthAdjust="spacing">'
            f"{safe}</text>"
        )
        if static:
            parts.append(text)
            continue

        parts.append(
            f'<clipPath id="r{ry}">'
            f'<rect x="{PAD}" y="{row_y:.1f}" height="{CELL_H}" width="0">'
            f'<animate attributeName="width" from="0" to="{ART_W}" '
            f'begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            "</rect></clipPath>"
        )
        parts.append(f'<g clip-path="url(#r{ry})">{text}</g>')
        parts.append(
            f'<rect y="{row_y + 1:.1f}" width="{CELL_W}" height="{CELL_H - 2}" '
            f'fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + ART_W}" '
            f'begin="{delay:.3f}s" dur="{ROW_DUR:.2f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.85" begin="{delay:.3f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{delay + ROW_DUR:.3f}s"/>'
            "</rect>"
        )

    status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
    status_y = status_line_y + 19
    parts.append(
        f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" '
        f'stroke="{FRAME}"/>'
    )
    parts.append(
        f'<text x="{PAD}" y="{status_y:.1f}" fill="{TITLE_TEXT}" font-size="13">'
        f'{PROMPT_HOST}:~$ whoami <tspan fill="{INK}">{html.escape(DISPLAY_NAME)}</tspan></text>'
    )
    # Cursor sits after "whoami NAME" — approximate monospace advance for status.
    cursor_x = PAD + 14 * (len(PROMPT_HOST) + len(":~$ whoami ") + len(DISPLAY_NAME))
    if static:
        parts.append(
            f'<rect x="{cursor_x}" y="{status_y - 12:.1f}" width="8" height="14" fill="{INK}"/>'
        )
    else:
        parts.append(
            f'<rect x="{cursor_x}" y="{status_y - 12:.1f}" width="8" height="14" fill="{INK}">'
            '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
            'dur="1s" repeatCount="indefinite"/></rect>'
        )
    parts.append("</svg>")
    return "".join(parts)


def write_ascii_svg(src: Path, out: Path, *, static: bool = STATIC) -> Path:
    """Sample ``src``, render SVG, write ``out``, and return ``out``."""
    rows = sample_rows(src)
    svg = render_ascii_svg(rows, static=static)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    LOGGER.info("Wrote %s (%d bytes; %dx%d)", out, len(svg), CANVAS_W, CANVAS_H)
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    src = Path(args[0]) if len(args) >= 1 else DEFAULT_SRC
    out = Path(args[1]) if len(args) >= 2 else DEFAULT_OUT
    try:
        write_ascii_svg(src, out)
    except AsciiSvgError as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
