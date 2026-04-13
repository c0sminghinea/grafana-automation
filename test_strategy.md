# Test Strategy — Grafana Synthetic Monitoring

## 1. Objective

Validate the core user-facing workflows of the Grafana Synthetic Monitoring plugin on `play.grafana.org`:

- **Filtering checks by probe (location)** — ensuring the filter produces accurate results.
- **Navigating to check detail pages** — ensuring the correct data is rendered.
- **Empty-state UX** — ensuring the UI handles zero-result filters gracefully.

> In Grafana Synthetic Monitoring, "locations" are implemented as **probes**. All references to probe filtering correspond to the "Filtering Checks by Location" requirement.

## 2. Scope

### In Scope

| Area | Coverage |
|---|---|
| Probe filter on the Checks page | Functional correctness (content match against API, detail-page cross-check) |
| Check detail page | Heading, URL, probe dropdown, probe tabs |
| Empty-state handling | Zero rows, empty message, page stability |
| Browser-back navigation | Filter state preservation |

### Out of Scope

| Area | Rationale |
|---|---|
| Other filter dimensions (Type, Status) | Not required by the assignment |
| Check creation / editing / deletion | Read-only demo instance |
| Cross-browser testing | Chrome specified in suite header; other browsers can be added via `--browser` flag |
| Accessibility / keyboard navigation | Can be a follow-up phase |
| Performance benchmarks (load times) | Not a functional requirement |

## 3. Test Approach

### 3.1 Manual Test Cases

Three manual test cases (TC-001 through TC-003) are documented in a separate **Manual_Test_Cases.pdf** deliverable with:

- Step-by-step instructions reproducible by any QA engineer.
- Pass/fail criteria with explicit expected results per step.
- Known defects and blocked criteria documented inline.
- Automation notes that translate directly into code.

### 3.2 Automation

All three test cases are automated using **Playwright for Python** with **pytest**.

**Why Playwright?**

| Criterion | Playwright | Selenium |
|---|---|---|
| Auto-wait for elements | Built-in | Requires explicit waits |
| API testing support | Native `APIRequestContext` | Requires separate library |
| SPA navigation handling | `wait_for_url`, condition-based waits | Custom polling logic |
| Selector strategies | Role, label, test-id, text, CSS | Primarily CSS/XPath |
| Browser install | `playwright install` | Manual driver management |
| Tracing / debugging | Built-in trace viewer | Screenshot-only |

### 3.3 Architecture — Page Object Model

All UI interactions are encapsulated in page objects under `pages/`:

- **`ChecksPage`** — navigation, search, probe filter, check card assertions, visible check ID extraction.
- **`CheckDetailPage`** — dashboard load wait, heading/URL assertions, probe dropdown and tab verification.

Tests never use raw Playwright locators directly. Each page-object method is annotated with `@allure.step` so the Allure report shows a clear action log.

### 3.4 Data Strategy

Tests are fully **data-driven** with no hardcoded values:

```
API (ground truth)  →  Random selection  →  UI interaction  →  Assert UI matches API
```

1. **Session-scoped API fixtures** fetch checks and probes once per test run.
2. **`random.choice()`** selects test subjects dynamically.
3. Expected values (IDs, probe names) are derived from the API response.
4. UI assertions compare **rendered content** (check IDs, probe names) against API-derived expectations — not superficial counts.

This design means the same suite runs against **demo, staging, and production** without code changes — only the `BASE_URL` environment variable changes.

### 3.5 Reproducibility

Each run uses a random seed for probe/check selection, printed in the test header:

```
random-seed: 1913181539  (rerun with --random-seed 1913181539)
```

To reproduce a specific run: `pytest --random-seed 1913181539`

### 3.6 Failure Artifacts

On test failure, the suite automatically captures and attaches to the Allure report:

| Artifact | Allure Attachment | Purpose |
|---|---|---|
| Screenshot | PNG image | Visual state at failure (captured in-memory, no disk file) |
| Playwright Trace | ZIP file | Full timeline: DOM snapshots, network, clicks (`traces/<test_name>.zip`) |

Traces can be viewed locally with: `playwright show-trace traces/<name>.zip`

### 3.7 Reporting — Allure

The suite uses **Allure** for rich test reporting:

- **Feature / Story grouping** — tests are tagged with `@allure.feature` and `@allure.story` for logical grouping.
- **Severity labels** — Critical for TC-001/TC-002, Normal for TC-003.
- **Flat step hierarchy** — page-object methods appear as top-level Allure steps; assertion blocks use named `allure.step` context managers.
- **Environment metadata** — base URL, random seed, browser, and viewport are written to `environment.properties`.
- **Defect categories** — `categories.json` classifies failures into Product Defects, Test Defects, and Known Issues.

### 3.8 CI/CD — GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/test.yml`) with two jobs:

1. **`test`** — installs dependencies, runs the suite, uploads Allure results and failure traces as artifacts.
2. **`report`** — generates the Allure report with run history and deploys it to GitHub Pages.

The workflow supports:
- Automatic runs on push/PR to `main`.
- Manual dispatch with an optional `random_seed` input for reproducibility.
- Configurable `GRAFANA_URL` via repository variables.

## 4. Environment

| Parameter | Value |
|---|---|
| Target instance | `https://play.grafana.org` (configurable via `BASE_URL`) |
| Browser | Chromium (latest, via Playwright) |
| Viewport | 1440 × 900 |
| Authentication | Anonymous access (play.grafana.org) |
| Python | 3.11+ |

### Environment Configuration

```
BASE_URL (env var)  ──┐
--base-url (CLI)    ──┤──▶  conftest.py  ──▶  API discovery  ──▶  tests
pytest.ini default  ──┘
```

The `conftest.py` discovers the SM datasource UID at runtime by querying `/api/datasources`, avoiding any hardcoded plugin identifiers.

## 5. Handling Dynamic Data and UI Elements

### Challenge: The demo instance has live, mutable data

**Solution**: Instead of relying on fixed test data, the suite:

- Fetches the **current** probe and check lists from the API before each run.
- Selects subjects **randomly** — each run may test a different probe or check.
- Computes expected values **from the API response**, never from constants.

### Challenge: Grafana is a React SPA with dynamic rendering

**Solution**:

- **Playwright auto-wait**: Every action waits for elements to be attached, visible, and stable.
- **Condition-based waits**: `expect().to_have_url()`, `expect().to_be_visible()`, and `wait_for(state="visible")` — zero static waits (`wait_for_timeout`) in the entire suite.
- **Lazy locators**: Playwright locators re-evaluate the DOM on every call — no stale-element exceptions.
- **Resilient selectors**: ARIA roles and accessible names first, `data-testid` second, text content last.

### Challenge: Probe names use camelCase internally

**Solution**: The suite uses API-returned probe names (e.g., `CapeTown`, `NorthVirginia`) directly for UI assertions, matching the format displayed in dropdowns and tabs.

## 6. Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| API endpoints require authentication | Tests cannot discover data | Clear error message in fixture; document auth setup in README |
| All probes have checks assigned | TC-003 cannot execute | `pytest.skip` with BLOCKED status; escalation path documented |
| Grafana UI upgrade changes selectors | Tests break | Selectors use roles/labels (not CSS classes); `playwright codegen` for quick updates |
| Demo instance data changes between runs | Assertions fail | Tests compute expectations from live API data, never from constants |
| Network latency causes timeouts | Flaky results | Playwright built-in defaults (30s navigation, 30s actions); 5s fast-fail click-retry in `click_view_dashboard_for_check`; TC-002 has `@pytest.mark.flaky(reruns=1)` for dashboard load timing |

## 7. Defect Tracking

| ID | Summary | Status | Affected TC |
|---|---|---|---|
| DEF-001 | No empty-state message when probe filter returns zero checks | Open | TC-003 step 9 |
| DEF-002 | "Used in X checks" link misapplies filter for multi-word probe names | Open | TC-001 (workaround: manual filter) |
| OBS-001 | Subtitle "0 of 0 total checks" — "total" is ambiguous | Under review | TC-003 |

## 8. Execution Cadence

| Trigger | Scope |
|---|---|
| Pre-release | Full suite against staging |
| Nightly CI | Full suite against demo |
| Post-deploy | Smoke subset (TC-001 + TC-002) |
| On-demand | Any marker subset (`pytest -m tc001`) |

## 9. Deliverables

| Artifact | File |
|---|---|
| Manual test cases | `Manual_Test_Cases.pdf` (separate deliverable) |
| Automation scripts | `tests/test_tc001_*.py`, `test_tc002_*.py`, `test_tc003_*.py` |
| Page objects | `pages/checks_page.py`, `pages/check_detail_page.py` |
| Shared fixtures | `conftest.py`, `helpers/api.py` |
| Execution instructions | `README.md` |
| This strategy document | `test_strategy.md` |
