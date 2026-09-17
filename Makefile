VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: all install lint format test check clean

all: check

$(VENV):
	uv venv $(VENV)

install: $(VENV)
	uv pip install -p $(VENV) -e ".[dev]"

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

format:
	$(BIN)/ruff check --fix .
	$(BIN)/ruff format .

test:
	$(BIN)/pytest

check: lint test

clean:
	rm -rf .pytest_cache .ruff_cache build dist
	find . -path ./$(VENV) -prune -o -name __pycache__ -type d -exec rm -rf {} +
