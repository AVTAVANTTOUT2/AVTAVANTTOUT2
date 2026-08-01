#!/usr/bin/env python3
"""Unit tests for photo prep (I/O mocked — no rembg model download)."""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prep_photo import PhotoPrepError, prep_photo  # noqa: E402


def test_prep_photo_missing_input(tmp_path: Path) -> None:
    with pytest.raises(PhotoPrepError, match="not found"):
        prep_photo(tmp_path / "missing.jpg", tmp_path / "out.png")


def test_prep_photo_composites_to_grayscale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    src = tmp_path / "face.png"
    out = tmp_path / "prepped.png"
    Image.new("RGB", (16, 16), color=(80, 80, 80)).save(src)

    fake_rgba = Image.new("RGBA", (16, 16), color=(90, 90, 90, 255))

    fake_rembg = types.ModuleType("rembg")
    fake_rembg.remove = lambda image: fake_rgba  # type: ignore[attr-defined]

    fake_cv2 = types.ModuleType("cv2")

    def _cvt(_rgb: np.ndarray, _code: int) -> np.ndarray:
        return np.full((16, 16), 90, dtype=np.uint8)

    class _Clahe:
        def apply(self, gray: np.ndarray) -> np.ndarray:
            return gray

    fake_cv2.cvtColor = _cvt  # type: ignore[attr-defined]
    fake_cv2.COLOR_RGB2GRAY = 7  # type: ignore[attr-defined]
    fake_cv2.createCLAHE = MagicMock(return_value=_Clahe())  # type: ignore[attr-defined]
    fake_cv2.convertScaleAbs = lambda gray, alpha=1.0, beta=0: gray  # type: ignore[attr-defined]
    fake_cv2.GaussianBlur = lambda mask, ksize, sigma: mask  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "rembg", fake_rembg)
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    width, height = prep_photo(src, out)

    assert width == 16 and height == 16
    assert out.is_file()
    result = Image.open(out)
    assert result.mode == "L"
    assert result.size == (16, 16)
    assert np.array(result).mean() < 250
