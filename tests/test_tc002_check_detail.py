"""TC-002 — Correct Check Detail Page Opens When Clicking View Dashboard."""

from __future__ import annotations

import logging
import re

import allure
import pytest
from playwright.sync_api import Page, expect

from helpers.api import pick_random_check
from pages.checks_page import ChecksPage
from pages.check_detail_page import CheckDetailPage

logger = logging.getLogger(__name__)


@allure.feature("Check Detail")
@allure.story("View dashboard navigates to correct detail page")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.tc002
@pytest.mark.flaky(reruns=2, reruns_delay=2, reason="play.grafana.org can be slow")
def test_correct_check_detail_opens(
    page: Page,
    checks_data: list[dict],
    probe_map: dict[int, str],
):
    # 1. Prepare Data
    selected = pick_random_check(checks_data)
    check_id = selected["id"]
    check_job = selected["job"]
    check_target = selected["target"]

    # Map API probe IDs to the names we expect in the UI
    probe_names = [probe_map.get(pid, f"Unknown ({pid})") for pid in selected.get("probes", [])]

    logger.info("Testing Check ID: %d | Job: %s", check_id, check_job)

    checks = ChecksPage(page)
    detail = CheckDetailPage(page)

    # 2. Navigate and Search
    checks.navigate()
    checks.search(check_job)

    # 3. Verify the Card in the list view
    with allure.step(f"Verify card for check {check_id} is visible"):
        checks.expect_check_card(check_job, check_target, len(probe_names))

    # 4. Action: Drill Down
    checks.click_view_dashboard_for_check(check_id)

    # 5. Assertions on Detail Page
    detail.wait_for_load()

    with allure.step("Verify URL and Heading"):
        expect(page).to_have_url(re.compile(rf"/checks/{check_id}"))
        detail.expect_heading_contains(check_job)

    # 6. Deep Data Validation
    with allure.step("Verify Probe Dropdown options"):
        dropdown_probes = detail.get_probe_dropdown_options(probe_names=probe_names)
        assert set(dropdown_probes) == set(probe_names), (
            f"Dropdown mismatch! Diff: {set(dropdown_probes) ^ set(probe_names)}"
        )

    with allure.step("Verify Probe Tabs/Content"):
        probe_tabs = detail.get_probe_tabs(expected_probes=probe_names)
        assert set(probe_tabs) == set(probe_names), (
            f"Tab mismatch! Diff: {set(probe_tabs) ^ set(probe_names)}"
        )
