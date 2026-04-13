"""Page Object for the Grafana Synthetic Monitoring Checks list page."""

from __future__ import annotations

import logging
import re

import allure
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)

SM_CHECKS_PATH = "/a/grafana-synthetic-monitoring-app/checks"


class ChecksPage:

    def __init__(self, page: Page):
        self.page = page
        self._subtitle = page.locator("text=/Currently showing/")
        self._search_box = page.get_by_role("textbox", name="Search checks")
        self._filters_button = page.get_by_role(
            "button", name=re.compile(r"Additional filters"),
        )
        self._filter_dialog = page.locator("[role='dialog']")
        self._probes_input = self._filter_dialog.locator("#check-probes-filter")
        self._dialog_close_button = (
            self._filter_dialog.locator("button").filter(has_text="Close").last
        )
        self._view_dashboard_links = page.get_by_role(
            "link", name="View dashboard",
        )
        self._empty_state_message = page.get_by_text(
            re.compile(r"no checks|no results|no data|no matching", re.IGNORECASE),
        )
        self._sort_control = page.get_by_text(re.compile(r"Sort|A-Z"))

    @allure.step("Navigate to Checks page")
    def navigate(self):
        logger.info("Navigating to Checks page: %s", SM_CHECKS_PATH)
        self.page.goto(SM_CHECKS_PATH)
        expect(self._subtitle).to_be_visible(timeout=10_000)

    @allure.step("Search for '{query}'")
    def search(self, query: str):
        logger.info("Searching for: '%s'", query)
        self._search_box.fill(query)
        expect(self._subtitle).to_be_visible()

    @allure.step("Apply probe filter: '{probe_display_name}'")
    def apply_probe_filter(self, probe_display_name: str):
        logger.info("Applying probe filter: '%s'", probe_display_name)
        self._filters_button.click()
        expect(self._filter_dialog).to_be_visible()

        self._probes_input.click()
        self._probes_input.fill(probe_display_name)
        self.page.get_by_role("option", name=probe_display_name).click()

        self._filter_dialog.locator("h2").click()
        self._dialog_close_button.click()
        expect(self._filter_dialog).not_to_be_visible()

    @allure.step("Assert filter active ({count} active)")
    def expect_filter_active(self, count: int = 1):
        expect(
            self.page.get_by_role(
                "button",
                name=re.compile(rf"Additional filters \({count} active\)"),
            ),
        ).to_be_visible()

    @allure.step("Click 'View dashboard' at index {index}")
    def click_view_dashboard(self, *, index: int = 0):
        logger.info("Clicking 'View dashboard' link at index %d", index)
        self._view_dashboard_links.nth(index).click()
        self.page.wait_for_url(re.compile(r"/checks/\d+"))

    @allure.step("Click 'View dashboard' for check {check_id}")
    def click_view_dashboard_for_check(self, check_id: int):
        """Retry click up to 3 times — React can swallow clicks during re-renders."""
        logger.info("Clicking 'View dashboard' for check %d", check_id)
        link = self.page.locator(f"a[href*='/checks/{check_id}']").filter(
            has_text="View dashboard",
        )
        expect(link).to_be_visible()

        for attempt in range(1, 4):
            link.click()
            try:
                self.page.wait_for_url(
                    re.compile(rf"/checks/{check_id}\b"),
                    timeout=5_000,
                )
                return
            except Exception:
                if attempt < 3:
                    logger.warning(
                        "Navigation did not occur after click (attempt %d/3), retrying",
                        attempt,
                    )
                else:
                    raise

    @allure.step("Assert check card: {job}")
    def expect_check_card(self, job: str, target: str, probe_count: int):
        expect(
            self.page.get_by_role("heading", name=job, exact=True).first
        ).to_be_visible()
        expect(
            self.page.get_by_text(target).first
        ).to_be_visible()
        expect(
            self.page.get_by_text(
                re.compile(rf"\b{probe_count}\s+location"),
            ).first
        ).to_be_visible()

    @allure.step("Get visible check IDs")
    def get_visible_check_ids(self) -> list[int]:
        return [
            int(m.group(1))
            for link in self._view_dashboard_links.all()
            if (m := re.search(r"/checks/(\d+)", link.get_attribute("href") or ""))
        ]

    @allure.step("Get check row count")
    def get_check_row_count(self) -> int:
        return self._view_dashboard_links.count()

    @allure.step("Wait for results")
    def wait_for_results(self):
        self._subtitle.wait_for(state="visible")

    @allure.step("Check for empty-state message")
    def has_empty_state_message(self) -> bool:
        if self._empty_state_message.count() > 0:
            expect(self._empty_state_message.first).to_be_visible()
            return True
        return False

    @allure.step("Assert structural elements visible")
    def expect_structural_elements_visible(self):
        expect(self._search_box).to_be_visible()
        expect(self._filters_button).to_be_visible()
        expect(self._sort_control.first).to_be_visible()

    @allure.step("Navigate back to checks list")
    def go_back_to_list(self):
        logger.info("Navigating back to checks list")
        self.page.go_back()
        expect(self._subtitle).to_be_visible()


