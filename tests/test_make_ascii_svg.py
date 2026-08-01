#!/usr/bin/env python3
"""Unit tests for ASCII glyph mapping and SVG assembly."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_ascii_svg as ascii_mod  # noqa: E402
from make_ascii_svg import (  # noqa: E402
    AsciiSvgError,
    luminance_to_glyph,
    render_ascii_svg,
    sample_rows,
    write_ascii_svg,
)


def test_luminance_to_glyph_white_is_space() -> None:
    assert luminance_to_glyph(0.99) == " "


def test_luminance_to_glyph_black_is_dense() -> None:
    glyph = luminance_to_glyph(0.0)
    assert glyph == ascii_mod.RAMP[-1]


def test_sample_rows_dimensions(tmp_path: Path) -> None:
    img_path = tmp_path / "face.png"
    Image.new("L", (40, 40), color=0).save(img_path)
    rows = sample_rows(img_path)
    assert len(rows) == ascii_mod.ROWS
    assert all(len(r) == ascii_mod.COLS for r in rows)
    assert all(ch == ascii_mod.RAMP[-1] for ch in rows[0])


def test_sample_rows_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AsciiSvgError, match="not found"):
        sample_rows(tmp_path / "nope.png")


def test_render_ascii_svg_static_has_no_animate() -> None:
    rows = [" " * ascii_mod.COLS for _ in range(ascii_mod.ROWS)]
    svg = render_ascii_svg(rows, static=True)
    assert "<animate" not in svg
    assert svg.startswith("<svg")


def test_render_ascii_svg_animated_has_clip_wipe() -> None:
    rows = ["#" * ascii_mod.COLS for _ in range(ascii_mod.ROWS)]
    svg = render_ascii_svg(rows, static=False)
    assert 'clipPath id="r0"' in svg
    assert "<animate" in svg


def test_render_ascii_svg_rejects_bad_shape() -> None:
    with pytest.raises(AsciiSvgError, match="Expected"):
        render_ascii_svg(["abc"], static=True)


def test_write_ascii_svg(tmp_path: Path) -> None:
    src = tmp_path / "src.png"
    out = tmp_path / "avi-ascii.svg"
    Image.new("L", (20, 20), color=128).save(src)
    write_ascii_svg(src, out, static=True)
    assert out.is_file()
    assert "portrait.sh" in out.read_text(encoding="utf-8")
