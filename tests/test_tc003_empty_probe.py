"""TC-003 — Probe With Zero Assigned Checks Produces an Empty List."""

from __future__ import annotations

import logging

import allure
import pytest
from playwright.sync_api import Page

from helpers.api import find_probe_without_checks, api_name_to_display
from pages.checks_page import ChecksPage

logger = logging.getLogger(__name__)


@allure.feature("Probe Filter")
@allure.story("Empty probe produces no-data state")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.tc003
def test_empty_probe_filter_shows_no_data(
    page: Page,
    checks_data: list[dict],
    probes_data: list[dict],
):
    # 1. Data Setup
    zero_probe = find_probe_without_checks(probes_data, checks_data)
    if zero_probe is None:
        pytest.skip("No unassigned probes found in this environment.")

    probe_display_name = api_name_to_display(zero_probe["name"])
    logger.info(
        "Selected zero-assignment probe: %s (display: '%s', id=%d)",
        zero_probe["name"], probe_display_name, zero_probe["id"],
    )

    checks = ChecksPage(page)

    # 2. Navigate and Filter
    checks.navigate()
    checks.apply_probe_filter(probe_display_name)
    checks.expect_filter_active()
    checks.wait_for_results()

    # 3. Assertions
    with allure.step("Verify list is empty"):
        row_count = checks.get_check_row_count()
        assert row_count == 0, f"Expected 0 check rows but found {row_count}"

    with allure.step("Verify page structural elements remain visible"):
        checks.expect_structural_elements_visible()

    # 4. Known Bug Documentation
    with allure.step("Verify empty-state message is displayed"):
        if not checks.has_empty_state_message():
            pytest.xfail(
                "Known defect: no empty-state message is shown when the filter "
                "produces zero results. The list area is completely blank."
            )
