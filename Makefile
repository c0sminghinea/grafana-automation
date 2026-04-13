.PHONY: install test report headed lint clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and Playwright browsers
	pip install -r requirements.txt
	playwright install chromium

test: ## Run all tests (headless)
	pytest

headed: ## Run tests in headed mode with slow-mo
	pytest --headed --slowmo 300

report: ## Generate and open Allure report
	allure serve allure-results

lint: ## Run ruff linter
	ruff check .

clean: ## Remove test artifacts
	rm -rf allure-results allure-report traces .pytest_cache
