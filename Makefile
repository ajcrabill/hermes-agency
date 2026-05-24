# HermesAgency — top-level make targets

.PHONY: help install test test-smoke test-seams lint typecheck audit clean dev

help:
	@echo "HermesAgency — common targets:"
	@echo "  make install       Install in editable mode (with dev extras)"
	@echo "  make test          Run the full test suite"
	@echo "  make test-smoke    Run end-to-end smoke tests only"
	@echo "  make test-seams    Run system-seam tests only"
	@echo "  make lint          Run ruff"
	@echo "  make typecheck     Run mypy"
	@echo "  make audit         Run the framework audit against itself (self-audit)"
	@echo "  make clean         Remove caches + build artifacts"

install:
	pip install -e ".[dev,embed]"

dev: install
	@echo "Editable install complete. Run 'make test' to verify the spine."

test:
	pytest

test-smoke:
	pytest -m smoke

test-seams:
	pytest -m seam

lint:
	ruff check _framework hermes_agency tests || true

typecheck:
	mypy _framework hermes_agency || true

audit:
	python _framework/audit/audit_alignment.py --self || true

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
