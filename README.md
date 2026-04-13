# Grafana Synthetic Monitoring — UI Automation Suite

Automated end-to-end tests for the [Grafana Synthetic Monitoring](https://play.grafana.org/a/grafana-synthetic-monitoring-app/home) plugin, covering probe filtering, check detail navigation, and empty-state handling.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11+ |
| pip | latest |
| Node.js | 18+ (required by Playwright's browser binaries) |

## Quick Start

```bash
# 1. Clone or copy this project
cd grafana-automation

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (one-time)
playwright install chromium

# 5. Install Allure CLI (for viewing reports)
brew install allure  # macOS
# For other OS: https://allurereport.org/docs/install/

# 6. Run all tests (headless)
pytest

# 7. Run in headed mode (for debugging / demo)
pytest --headed --slowmo 300
```

## Configuration

### Base URL

The default target is `https://play.grafana.org` (set in `pytest.ini`).  
Override it in any of these ways:

```bash
# Environment variable
BASE_URL=https://staging.grafana.example.com pytest

# CLI flag
pytest --base-url https://staging.grafana.example.com
```

No URL in the test suite is hardcoded—only the `BASE_URL` / `--base-url` value changes between environments.

### Browser

Playwright defaults to **Chromium**.  Run on other browsers:

```bash
pytest --browser firefox
pytest --browser webkit
```

### Viewport

The browser context is configured to **1440 × 900** (`conftest.py → browser_context_args`), matching the test suite specification.

### Reproducibility

Each run uses a random seed for probe/check selection. The seed is printed in the test header:

```
random-seed: 1913181539  (rerun with --random-seed 1913181539)
```

To reproduce a specific run:

```bash
pytest --random-seed 1913181539
```

---

## Running Tests

```bash
# All tests
pytest

# Single test case by marker
pytest -m tc001
pytest -m tc002
pytest -m tc003

# Verbose output
pytest -v

# Reproduce a specific run
pytest --random-seed 12345
```

### Allure Report

Allure results are generated automatically in `allure-results/` on every run.

```bash
# Generate and open the interactive HTML report
allure serve allure-results

# Or generate a static report
allure generate allure-results -o allure-report --clean
allure open allure-report
```

The report includes:
- **Overview dashboard** with pass/fail/xfail breakdown
- **Feature and story grouping** (Probe Filter, Check Detail)
- **Flat step hierarchy** — page-object methods appear as top-level steps (`@allure.step`), with named assertion steps for raw `assert` statements
- **Environment metadata** (base URL, random seed, browser, viewport)
- **Screenshots and Playwright traces** attached to failed tests
- **Severity labels** (Critical for TC-001/TC-002, Normal for TC-003)
- **Defect categories** (Product Defects, Test Defects, Known Issues)

---

## Project Structure

```
grafana-automation/
├── .github/
│   └── workflows/
│       └── test.yml              # CI pipeline: test + Allure report → GitHub Pages
├── conftest.py                   # Session fixtures, API discovery, failure artifacts
├── pytest.ini                    # Pytest settings, markers, base_url
├── requirements.txt              # Python dependencies
├── categories.json               # Allure defect classification categories
├── Makefile                      # Developer shortcuts (install, test, report, lint, clean)
├── test_strategy.md              # Test strategy document
├── README.md                     # ← you are here
├── pages/
│   ├── __init__.py               # Package init
│   ├── checks_page.py           # Page Object: Checks listing page
│   └── check_detail_page.py     # Page Object: Check dashboard / detail page
├── helpers/
│   ├── __init__.py
│   └── api.py                    # API data-selection logic (random probe/check)
└── tests/
    ├── __init__.py
    ├── test_tc001_probe_filter.py      # TC-001: Probe filter verification (3 probes)
    ├── test_tc002_check_detail.py      # TC-002: Check detail page verification
    └── test_tc003_empty_probe.py       # TC-003: Empty probe → no-data handling
```

---

## Test Case Summary

| TC | Title | Priority | What it verifies |
|---|---|---|---|
| TC-001 | Probe filter shows the correct checks | High | Parameterized across 3 random probes. For each: filters, asserts displayed check IDs match API, samples detail pages to confirm the probe in the dropdown |
| TC-002 | Correct check detail page opens | High | Picks a random check, searches by job name, verifies heading, URL, probe dropdown names, and probe tab names against API ground truth |
| TC-003 | Zero-assignment probe → empty list | Medium | Finds an unused probe, asserts 0 rows, checks for empty-state message (known defect → `xfail`), verifies page structural stability |

---

## Handling Dynamic Data and UI Elements

### Data-Driven Test Selection

Tests **never hardcode** check IDs, probe names, or expected counts.  Instead:

1. **Session-scoped API fixtures** (`conftest.py`) fetch checks and probes once per run.
2. **`helpers/api.py`** selects test subjects at random, computing expected values from the API response.
3. Tests assert the UI content (IDs, names) against API-derived ground truth — not superficial counts.

This means the same suite runs against **demo, staging, and production** without code changes — only `BASE_URL` changes.

### Page Object Model

All UI interactions are encapsulated in page objects under `pages/`:

- **`ChecksPage`** — navigation, search, probe filter, check card assertions, visible check ID extraction
- **`CheckDetailPage`** — dashboard load wait, heading/URL assertions, probe dropdown and tab verification

Tests never use raw Playwright locators directly.

### Selector Strategy

Selectors follow this priority order (most resilient first):

1. **ARIA roles and accessible names** — `get_by_role("button", name=...)`
2. **`data-testid` attributes** — `locator("[data-testid*='...']")`
3. **Text content** — `get_by_text(...)`, used for headings and labels

> If Grafana is upgraded and a selector breaks, use `playwright codegen <URL>` to discover updated selectors.

---

## Failure Artifacts

On test failure, the suite automatically captures and **attaches to the Allure report**:

| Artifact | Allure Attachment | Usage |
|---|---|---|
| Screenshot | PNG image | Visual state at failure (captured in-memory, no disk file) |
| Playwright Trace | ZIP file | Full timeline: clicks, network, DOM snapshots (`traces/<test_name>.zip`) |

View a trace locally with:

```bash
playwright show-trace traces/test_correct_check_detail_opens_chromium.zip
```

---

## Known Test Behaviors

| Behavior | Details |
|---|---|
| **TC-001 parameterized** | Runs against 3 randomly selected probes per execution. Each appears as a separate test item in the report. |
| **TC-002 retry** | Has `@pytest.mark.flaky(reruns=1)` for dashboard load timing on the public demo. Other tests do not retry. |
| **TC-003 `xfail`** | The empty-state message assertion is expected to fail (known defect DEF-001). Pytest reports `xfail`, not a hard failure. |
| **TC-003 `skip`** | If all probes have at least one check, the test is marked `BLOCKED` via `pytest.skip`. |

---

## CI/CD Integration

The project includes a full GitHub Actions workflow (`.github/workflows/test.yml`) with two jobs:

1. **`test`** — Installs dependencies, runs the suite, uploads Allure results and failure artifacts.
2. **`report`** — Generates the Allure report with run history and deploys it to **GitHub Pages**.

The workflow supports:
- Automatic runs on push/PR to `main`
- Manual dispatch with an optional `random_seed` input for reproducibility
- Configurable `GRAFANA_URL` via repository variables

For CI environments, use `playwright install --with-deps` to install OS-level dependencies (fonts, libraries).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `GET /api/datasources → 401` | The Grafana instance requires authentication. Anonymous API access must be enabled. |
| Selectors find 0 elements | Run `playwright codegen <URL>` to inspect the current DOM and update selectors. |
| Tests are flaky on slow networks | Playwright's built-in timeouts (30 s navigation, 30 s actions) apply by default. Override per-action with `timeout=` if needed. |
| TC-003 skips every run | All probes have checks assigned. Ensure at least one probe has zero check assignments. |
| Reproduce a specific failure | Rerun with the logged seed: `pytest --random-seed <N>` |
