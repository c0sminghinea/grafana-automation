"""TC-001 — Probe Filter Shows the Correct Checks."""

from __future__ import annotations

import logging

import allure
import pytest
from playwright.sync_api import Page

from helpers.api import find_n_probes_with_checks, api_name_to_display
from pages.checks_page import ChecksPage
from pages.check_detail_page import CheckDetailPage

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def _probe_samples(probes_data, checks_data):
    return find_n_probes_with_checks(probes_data, checks_data, n=3)


@pytest.fixture(params=[0, 1, 2], ids=lambda i: f"probe-{i + 1}")
def probe_and_count(request, _probe_samples):
    idx = request.param
    if idx >= len(_probe_samples):
        pytest.skip("Fewer than 3 probes with checks available")
    return _probe_samples[idx]


@allure.feature("Probe Filter")
@allure.story("Filter checks by probe location")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.tc001
def test_probe_filter_produces_expected_results(
    page: Page,
    checks_data: list[dict],
    probe_and_count: tuple,
):
    # 1. Data Setup
    selected_probe, expected_count = probe_and_count
    probe_api_name = selected_probe["name"]
    probe_display_name = api_name_to_display(probe_api_name)
    expected_ids = {
        c["id"] for c in checks_data
        if selected_probe["id"] in c.get("probes", [])
    }
    logger.info(
        "Selected probe: %s (display: '%s', id=%d) | expected checks: %d %s",
        probe_api_name, probe_display_name, selected_probe["id"],
        expected_count, sorted(expected_ids),
    )

    checks = ChecksPage(page)
    detail = CheckDetailPage(page)

    # 2. Navigate and Filter
    checks.navigate()
    checks.apply_probe_filter(probe_display_name)
    checks.expect_filter_active()

    # 3. Verify filtered results match API ground truth
    with allure.step(f"Verify displayed check IDs match API ({expected_count} checks)"):
        displayed_ids = set(checks.get_visible_check_ids())
        assert displayed_ids == expected_ids, (
            f"Displayed checks {sorted(displayed_ids)} don't match API-expected "
            f"checks {sorted(expected_ids)} for probe '{probe_api_name}'"
        )

    # 4. Deep Validation — sample detail pages to confirm probe in dropdown
    sample_size = min(3, len(displayed_ids))
    for i in range(sample_size):
        with allure.step(f"Verify detail page {i + 1}/{sample_size} contains probe '{probe_display_name}'"):
            checks.click_view_dashboard(index=i)
            detail.wait_for_load()
            detail.expect_probe_in_dropdown(probe_api_name)
            checks.go_back_to_list()
            checks.expect_filter_active()
