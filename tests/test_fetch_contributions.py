#!/usr/bin/env python3
"""Unit tests for contribution scraping and streak math."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_contributions import (  # noqa: E402
    FetchError,
    build_data,
    compute_current_streak,
    compute_longest_streak,
    fetch_html,
    parse_count_from_tooltip,
    parse_days,
    write_contributions,
)


SAMPLE_HTML = """
<table>
  <tbody>
    <tr>
      <td id="contribution-day-cell-0" class="ContributionCalendar-day" data-date="2026-01-01" data-level="0"></td>
      <td id="contribution-day-cell-1" class="ContributionCalendar-day" data-date="2026-01-02" data-level="2"></td>
      <td id="contribution-day-cell-2" class="ContributionCalendar-day" data-date="2026-01-03" data-level="3"></td>
      <td id="contribution-day-cell-3" class="ContributionCalendar-day" data-date="2026-01-04" data-level="0"></td>
      <td id="contribution-day-cell-4" class="ContributionCalendar-day" data-date="2026-01-05" data-level="1"></td>
    </tr>
  </tbody>
</table>
<tool-tip for="contribution-day-cell-0">No contributions on January 1st.</tool-tip>
<tool-tip for="contribution-day-cell-1">4 contributions on January 2nd.</tool-tip>
<tool-tip for="contribution-day-cell-2">12 contributions on January 3rd.</tool-tip>
<tool-tip for="contribution-day-cell-3">No contributions on January 4th.</tool-tip>
<tool-tip for="contribution-day-cell-4">1 contribution on January 5th.</tool-tip>
"""


def test_parse_count_from_tooltip_no_contributions() -> None:
    assert parse_count_from_tooltip("No contributions on January 1st.") == 0


def test_parse_count_from_tooltip_numbered() -> None:
    assert parse_count_from_tooltip("12 contributions on January 3rd.") == 12


def test_parse_count_from_tooltip_empty() -> None:
    assert parse_count_from_tooltip("") == 0


def test_parse_count_rejects_injection_noise() -> None:
    assert parse_count_from_tooltip("<script>alert(1)</script>") == 0


def test_parse_days_extracts_sorted_counts() -> None:
    days = parse_days(SAMPLE_HTML)
    assert [d["date"] for d in days] == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
    ]
    assert [d["count"] for d in days] == [0, 4, 12, 0, 1]


def test_parse_days_raises_when_markup_missing() -> None:
    with pytest.raises(FetchError, match="No calendar cells"):
        parse_days("<html><body>empty</body></html>")


def test_compute_current_streak_ignores_trailing_zero_today() -> None:
    days = [
        {"date": "2026-01-01", "count": 1},
        {"date": "2026-01-02", "count": 2},
        {"date": "2026-01-03", "count": 0},
    ]
    length, start, end = compute_current_streak(days)
    assert length == 2
    assert start == "2026-01-01"
    assert end == "2026-01-02"


def test_compute_current_streak_zero_when_idle() -> None:
    days = [
        {"date": "2026-01-01", "count": 0},
        {"date": "2026-01-02", "count": 0},
    ]
    assert compute_current_streak(days) == (0, None, None)


def test_compute_longest_streak() -> None:
    days = [
        {"date": "2026-01-01", "count": 1},
        {"date": "2026-01-02", "count": 1},
        {"date": "2026-01-03", "count": 0},
        {"date": "2026-01-04", "count": 2},
        {"date": "2026-01-05", "count": 3},
        {"date": "2026-01-06", "count": 4},
    ]
    length, start, end = compute_longest_streak(days)
    assert length == 3
    assert start == "2026-01-04"
    assert end == "2026-01-06"


def test_build_data_aggregates_stats() -> None:
    days = parse_days(SAMPLE_HTML)
    data = build_data(days, username="tester")
    assert data["username"] == "tester"
    assert data["total_contributions"] == 17
    assert data["active_days"] == 3
    assert data["best_day"] == {"date": "2026-01-03", "count": 12}
    assert data["monthly"][0]["month"] == "2026-01"
    assert data["monthly"][0]["total"] == 17


def test_fetch_html_timeout_raises_fetch_error() -> None:
    with patch("fetch_contributions.requests.get", side_effect=requests.Timeout("slow")):
        with pytest.raises(FetchError, match="Timed out"):
            fetch_html("https://example.com/users/x/contributions")


def test_fetch_html_http_error_raises_fetch_error() -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = requests.HTTPError("404")
    with patch("fetch_contributions.requests.get", return_value=response):
        with pytest.raises(FetchError, match="HTTP error"):
            fetch_html("https://example.com/users/x/contributions")


def test_write_contributions_roundtrip(tmp_path: Path) -> None:
    out = tmp_path / "contributions.json"
    with patch("fetch_contributions.fetch_html", return_value=SAMPLE_HTML):
        data = write_contributions(out, username="tester")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["total_contributions"] == data["total_contributions"] == 17
    assert loaded["username"] == "tester"
