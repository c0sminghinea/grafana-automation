"""API data-selection helpers for Grafana Synthetic Monitoring tests."""

from __future__ import annotations

import re
import random
from typing import Any


def api_name_to_display(name: str) -> str:
    """
    >>> api_name_to_display('CapeTown')
    'Cape Town'
    >>> api_name_to_display('NorthVirginia')
    'North Virginia'
    >>> api_name_to_display('Paris')
    'Paris'
    """
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', name)


def _count_checks_by_probe(checks: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for check in checks:
        for pid in check.get("probes", []):
            counts[pid] = counts.get(pid, 0) + 1
    return counts


def find_n_probes_with_checks(
    probes: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    n: int = 3,
) -> list[tuple[dict[str, Any], int]]:
    """Select up to *n* random probes that each have at least one check."""
    counts = _count_checks_by_probe(checks)
    candidates = [p for p in probes if p["id"] in counts]
    selected = random.sample(candidates, min(n, len(candidates)))
    return [(p, counts[p["id"]]) for p in selected]


def find_probe_without_checks(
    probes: list[dict[str, Any]],
    checks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Select a random probe with zero check assignments, or None."""
    ids_in_use = {pid for check in checks for pid in check.get("probes", [])}
    candidates = [p for p in probes if p["id"] not in ids_in_use]
    return random.choice(candidates) if candidates else None


def pick_random_check(checks: list[dict[str, Any]]) -> dict[str, Any]:
    return random.choice(checks)
