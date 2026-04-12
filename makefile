
VENV := venv
PYTHON_SYS := $(shell command -v python3 2> /dev/null)
PIP := $(VENV)/bin/pip
PYTHON := $(VENV)/bin/python
WATCHDOG := $(VENV)/bin/watchmedo

.PHONY: run venv check-python clean clean-venv

run: clean-venv venv
	@echo "--- Starting Watchdog (Auto-reload on save) ---"
	$(WATCHDOG) auto-restart --patterns="*.py" --recursive -- $(PYTHON) index.py

clean-venv:
	@echo "Deleting old virtual environment..."
	rm -rf $(VENV)

venv: check-python
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv $(VENV); \
	fi
	@echo "Updating pip and installing requirements..."
	$(PIP) install --upgrade pip
	@if [ -f "r.txt" ]; then \
		$(PIP) install -r r.txt; \
	else \
		echo "Warning: r.txt not found. Installing watchdog only."; \
	fi
	@echo "Installing Playwright browsers..."
	$(VENV)/bin/playwright install chromium
	@echo "Installing Watchdog..."
	$(PIP) install watchdog

check-python:
	@if [ -z "$(PYTHON_SYS)" ]; then \
		echo "Python3 not found. Attempting to install via DNF..."; \
		sudo dnf install -y python3; \
	else \
		echo "Python3 found at $(PYTHON_SYS)"; \
	fi

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +