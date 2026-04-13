"""Root conftest — shared fixtures for the Grafana Synthetic Monitoring test suite."""

from __future__ import annotations

import os
import random
import shutil
import logging
from pathlib import Path
from typing import Any, Generator

import allure
import pytest
from playwright.sync_api import APIRequestContext, Playwright

logger = logging.getLogger(__name__)

TRACE_DIR = Path("traces")


def pytest_addoption(parser):
    parser.addoption(
        "--random-seed", action="store", default=None, type=int,
        help="Seed for random.choice() selections. Enables deterministic reruns.",
    )


def pytest_configure(config):
    seed = (
        config.getoption("--random-seed", default=None)
        or os.environ.get("RANDOM_SEED")
    )
    if seed is not None:
        seed = int(seed)
    else:
        seed = random.randint(0, 2**31 - 1)
    random.seed(seed)
    config._random_seed = seed

    env_url = os.environ.get("BASE_URL")
    if env_url:
        config.option.base_url = env_url


def pytest_report_header(config):
    seed = getattr(config, "_random_seed", None)
    return f"random-seed: {seed}  (rerun with --random-seed {seed})"


def pytest_sessionfinish(session):
    """Write Allure environment.properties and copy categories.json."""
    allure_dir_str = getattr(session.config.option, "allure_report_dir", None)
    if not allure_dir_str:
        return

    allure_dir = Path(allure_dir_str)
    allure_dir.mkdir(parents=True, exist_ok=True)

    env_file = allure_dir / "environment.properties"
    seed = getattr(session.config, "_random_seed", "unknown")
    base_url = session.config.option.base_url
    env_file.write_text(
        f"Base.URL={base_url}\n"
        f"Random.Seed={seed}\n"
        f"Browser=Chromium (Playwright)\n"
        f"Viewport=1440x900\n"
    )

    categories_src = Path(__file__).parent / "categories.json"
    if categories_src.exists():
        shutil.copy(categories_src, allure_dir / "categories.json")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
    }


@pytest.fixture(scope="session")
def _api(playwright: Playwright, pytestconfig) -> Generator[APIRequestContext]:
    ctx = playwright.request.new_context(
        base_url=pytestconfig.getoption("base_url"),
    )
    yield ctx
    ctx.dispose()


@pytest.fixture(scope="session")
def sm_datasource_uid(_api: APIRequestContext) -> str:
    """Discover the Synthetic Monitoring datasource UID via API."""
    resp = _api.get("/api/datasources")
    assert resp.ok, (
        f"GET /api/datasources → {resp.status}. "
        "Ensure BASE_URL is correct and the Grafana instance allows anonymous API access."
    )
    for ds in resp.json():
        if "synthetic-monitoring" in ds.get("type", ""):
            logger.info("SM datasource UID: %s  (name: %s)", ds["uid"], ds.get("name"))
            return ds["uid"]
    pytest.fail("No datasource with type containing 'synthetic-monitoring' found.")


def _fetch_sm_resource(
    api: APIRequestContext, uid: str, endpoint: str,
) -> list[dict[str, Any]]:
    url = f"/api/datasources/proxy/uid/{uid}/sm/{endpoint}"
    resp = api.get(url)
    assert resp.ok, f"GET {endpoint} → {resp.status}"
    data = resp.json()
    logger.info("Fetched %d items from %s", len(data), endpoint)
    return data


@pytest.fixture(scope="session")
def checks_data(_api: APIRequestContext, sm_datasource_uid: str) -> list[dict[str, Any]]:
    return _fetch_sm_resource(_api, sm_datasource_uid, "check/list?includeAlerts=true")


@pytest.fixture(scope="session")
def probes_data(_api: APIRequestContext, sm_datasource_uid: str) -> list[dict[str, Any]]:
    return _fetch_sm_resource(_api, sm_datasource_uid, "probe/list")


@pytest.fixture(scope="session")
def probe_map(probes_data: list[dict[str, Any]]) -> dict[int, str]:
    return {p["id"]: p["name"] for p in probes_data}


@pytest.fixture(autouse=True)
def _capture_artifacts_on_failure(request):
    """Start tracing and attach screenshot + trace to Allure on failure."""
    if "page" not in request.fixturenames:
        yield
        return

    page = request.getfixturevalue("page")
    page.context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield
    rep = getattr(request.node, "rep_call", None)
    if rep and rep.failed:
        name = request.node.name.replace("[", "_").replace("]", "")
        TRACE_DIR.mkdir(exist_ok=True)
        trace_path = TRACE_DIR / f"{name}.zip"
        allure.attach(
            page.screenshot(),
            name="Screenshot on failure",
            attachment_type=allure.attachment_type.PNG,
        )
        page.context.tracing.stop(path=str(trace_path))
        allure.attach.file(
            str(trace_path),
            name="Playwright trace",
            attachment_type=allure.attachment_type.ZIP,
        )
    else:
        page.context.tracing.stop()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)