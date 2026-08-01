#!/usr/bin/env python3
"""Scrape public GitHub contribution calendar HTML — no token required.

Fetches ``https://github.com/users/<username>/contributions``, parses day
cells with BeautifulSoup, and writes ``data/contributions.json`` with raw
days plus derived stats (current streak, longest streak, best day, monthly).

Run daily by ``.github/workflows/update-profile-art.yml``.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from config import HTTP_TIMEOUT_SECONDS, HTTP_USER_AGENT, USERNAME

LOGGER = logging.getLogger("fetch_contributions")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_OUT = ROOT / "data" / "contributions.json"
CONTRIBUTIONS_URL = f"https://github.com/users/{USERNAME}/contributions"


class DayCount(TypedDict):
    """One calendar day contribution count."""

    date: str
    count: int


class FetchError(Exception):
    """Raised when contribution scraping fails."""


def fetch_html(url: str = CONTRIBUTIONS_URL) -> str:
    """GET the public contributions fragment and return response text."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": HTTP_USER_AGENT},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.Timeout as exc:
        raise FetchError(
            f"Timed out after {HTTP_TIMEOUT_SECONDS}s fetching contributions for "
            f"user {USERNAME} from {url}"
        ) from exc
    except requests.RequestException as exc:
        raise FetchError(
            f"HTTP error fetching contributions for user {USERNAME} from {url}: {exc}"
        ) from exc
    return resp.text


def parse_count_from_tooltip(text: str) -> int:
    """Parse a GitHub tooltip string into an integer contribution count."""
    cleaned = text.strip()
    if not cleaned:
        return 0
    if re.search(r"no contributions", cleaned, re.I):
        return 0
    match = re.match(r"(\d+)", cleaned)
    return int(match.group(1)) if match else 0


def parse_days(html: str) -> list[DayCount]:
    """Parse contribution day cells from GitHub calendar HTML."""
    soup = BeautifulSoup(html, "html.parser")
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        # Newer markup sometimes uses <td> with role / data-level only.
        cells = soup.select("[data-date].ContributionCalendar-day, td[data-date]")
    if not cells:
        raise FetchError(
            f"No calendar cells found for user {USERNAME}; GitHub markup may have changed"
        )

    days: list[DayCount] = []
    for cell in cells:
        if not isinstance(cell, Tag):
            continue
        date = cell.get("data-date")
        if not isinstance(date, str) or not date:
            continue

        # Prefer tooltip text; fall back to data-level / data-count attributes.
        count: int | None = None
        td_id = cell.get("id")
        if isinstance(td_id, str) and td_id:
            tooltip_el = soup.find("tool-tip", attrs={"for": td_id})
            if isinstance(tooltip_el, Tag):
                count = parse_count_from_tooltip(tooltip_el.get_text(strip=True))

        if count is None:
            raw_count = cell.get("data-count")
            if isinstance(raw_count, str) and raw_count.isdigit():
                count = int(raw_count)
            else:
                level = cell.get("data-level")
                # data-level is a bucket, not a count — treat unknown as 0.
                count = 0 if level in (None, "0", 0) else 1

        days.append({"date": date, "count": count})

    if not days:
        raise FetchError(f"Parsed zero contribution days for user {USERNAME}")

    days.sort(key=lambda d: d["date"])
    return days


def compute_current_streak(days: list[DayCount]) -> tuple[int, str | None, str | None]:
    """Return ``(length, start, end)`` for the current contribution streak."""
    if not days:
        return 0, None, None
    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today may still be empty — don't break the streak yet
    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days: list[DayCount]) -> tuple[int, str | None, str | None]:
    """Return ``(length, start, end)`` for the longest contribution streak."""
    longest = run = 0
    longest_start = longest_end = None
    run_start_idx: int | None = None
    for i, day in enumerate(days):
        if day["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest and run_start_idx is not None:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
            run_start_idx = None
    return longest, longest_start, longest_end


def build_data(days: list[DayCount], username: str = USERNAME) -> dict[str, Any]:
    """Derive summary stats and return the serializable contributions payload."""
    if not days:
        raise FetchError(f"Cannot build contribution data for user {username}: empty days")

    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"])
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly: dict[str, int] = {}
    for day in days:
        key = day["date"][:7]
        monthly[key] = monthly.get(key, 0) + day["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    return {
        "username": username,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "days": days,
    }


def write_contributions(
    out_path: Path = DEFAULT_OUT,
    *,
    username: str = USERNAME,
) -> dict[str, Any]:
    """Fetch, parse, write JSON, and return the payload."""
    url = f"https://github.com/users/{username}/contributions"
    html = fetch_html(url)
    days = parse_days(html)
    data = build_data(days, username=username)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    LOGGER.info(
        "Wrote %s: %s contributions, current streak %s, longest streak %s",
        out_path,
        data["total_contributions"],
        data["current_streak"]["length"],
        data["longest_streak"]["length"],
    )
    return data


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = list(sys.argv[1:] if argv is None else argv)
    out = Path(args[0]) if len(args) >= 1 else DEFAULT_OUT
    try:
        write_contributions(out)
    except FetchError as exc:
        LOGGER.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
