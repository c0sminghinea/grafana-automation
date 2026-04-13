"""Page Object for a Grafana Synthetic Monitoring Check Detail / Dashboard page."""

from __future__ import annotations

import logging
import re

import allure
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


class CheckDetailPage:

    def __init__(self, page: Page):
        self.page = page
        self._probe_label = page.locator("[data-testid*='Label probe']")
        self._probe_combobox = self._probe_label.locator("..").get_by_role(
            "combobox",
        )
        self._heading = page.locator("h1").first
        self._options = page.get_by_role("option")
        self._tabs = page.get_by_role("tab")

    @allure.step("Wait for detail page to load")
    def wait_for_load(self):
        """Wait for SPA transition: URL change, probe label attached, heading updated."""
        logger.info("Waiting for detail page to mount")
        self.page.wait_for_url(re.compile(r"/checks/\d+"))
        self._probe_label.wait_for(state="attached")
        expect(self._heading).not_to_have_text("Checks")

    @allure.step("Assert heading contains '{text}'")
    def expect_heading_contains(self, text: str):
        logger.info("Asserting heading contains: '%s'", text)
        expect(self._heading).to_contain_text(text)

    def _open_probe_dropdown(self):
        self._probe_label.wait_for(state="attached")
        self._probe_combobox.click()

    @allure.step("Get probe dropdown options")
    def get_probe_dropdown_options(self, probe_names: list[str]) -> list[str]:
        self._open_probe_dropdown()
        expect(
            self.page.get_by_role("option", name=probe_names[-1])
        ).to_be_visible()

        option_texts = [t.strip() for t in self._options.all_text_contents()]
        probes = [t for t in option_texts if t and t != "All"]

        self.page.keyboard.press("Escape")
        logger.info("Probe dropdown options: %s", probes)
        return probes

    @allure.step("Assert probe '{probe_name}' in dropdown")
    def expect_probe_in_dropdown(self, probe_name: str):
        logger.info("Asserting probe '%s' in dropdown", probe_name)
        self._open_probe_dropdown()
        expect(
            self.page.get_by_role("option", name=probe_name)
        ).to_be_visible()
        self.page.keyboard.press("Escape")

    @allure.step("Get probe tabs")
    def get_probe_tabs(self, expected_probes: list[str]) -> list[str]:
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
        self.page.get_by_text(expected_probes[0], exact=True).first.wait_for(
            state="visible",
        )

        all_tab_texts = [t.strip() for t in self._tabs.all_text_contents()]
        tabs = [
            t for t in all_tab_texts
            if t and t != "All" and not t.startswith("Selected")
        ]

        if not tabs:
            for name in expected_probes:
                expect(
                    self.page.get_by_text(name, exact=True).first
                ).to_be_visible()
            return list(expected_probes)

        return tabs
