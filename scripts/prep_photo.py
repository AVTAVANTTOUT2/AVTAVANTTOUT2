#!/usr/bin/env python3
"""Prepare a portrait photo for clean ASCII conversion.

Pipeline:
  1. Remove the background with rembg so the subject is isolated.
  2. Boost local contrast with OpenCV CLAHE.
  3. Composite onto pure white so the background maps to ASCII spaces.

Output defaults to ``source-prepped.png`` (grayscale), consumed by
``make_ascii_svg.py``. Run once whenever the source photo changes.

Usage:
    python scripts/prep_photo.py [input.jpg] [output.png]
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LOGGER = logging.getLogger("prep_photo")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_INPUT = ROOT / "source-photo.jpg"
DEFAULT_OUTPUT = ROOT / "source-prepped.png"

CLAHE_CLIP_LIMIT = float(os.environ.get("PREP_CLAHE_CLIP", "2.6"))
CLAHE_TILE = int(os.environ.get("PREP_CLAHE_TILE", "8"))
SCALE_ALPHA = float(os.environ.get("PREP_SCALE_ALPHA", "1.05"))
SCALE_BETA = float(os.environ.get("PREP_SCALE_BETA", "18"))
MASK_BLUR_SIGMA = float(os.environ.get("PREP_MASK_BLUR", "1.0"))


class PhotoPrepError(Exception):
    """Raised when photo preparation fails at a system boundary."""


def prep_photo(input_path: Path, output_path: Path) -> tuple[int, int]:
    """Prepare ``input_path`` and write a grayscale PNG to ``output_path``.

    Returns:
        The ``(width, height)`` of the written image.

    Raises:
        PhotoPrepError: If the input is missing or unreadable.
    """
    if not input_path.is_file():
        raise PhotoPrepError(f"Input photo not found: {input_path}")

    try:
        import cv2
        from rembg import remove
    except ImportError as exc:
        raise PhotoPrepError(
            "Portrait prep requires opencv-python and rembg. "
            "Install with: pip install -r scripts/requirements.txt"
        ) from exc

    try:
        source = Image.open(input_path).convert("RGBA")
    except OSError as exc:
        raise PhotoPrepError(f"Unable to open photo {input_path}: {exc}") from exc

    LOGGER.debug("Removing background from %s", input_path)
    cut = remove(source)
    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.split()[-1])

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP_LIMIT,
        tileGridSize=(CLAHE_TILE, CLAHE_TILE),
    )
    gray = clahe.apply(gray)
    gray = cv2.convertScaleAbs(gray, alpha=SCALE_ALPHA, beta=SCALE_BETA)

    mask = alpha.astype(np.float32) / 255.0
    mask = cv2.GaussianBlur(mask, (0, 0), MASK_BLUR_SIGMA)
    out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
    out = np.clip(out, 0, 255).astype(np.uint8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, mode="L").save(output_path)
    height, width = out.shape
    LOGGER.info("Wrote %s (%dx%d)", output_path, width, height)
    return width, height


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    input_path = Path(args[0]) if len(args) >= 1 else DEFAULT_INPUT
    output_path = Path(args[1]) if len(args) >= 2 else DEFAULT_OUTPUT
    try:
        prep_photo(input_path, output_path)
    except PhotoPrepError as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
