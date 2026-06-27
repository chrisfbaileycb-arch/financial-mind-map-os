.PHONY: install ui seed sync serve run test lint demo clean help

help:
	@echo "Financial Mind-Map OS — common tasks:"
	@echo "  make install   Install Python deps (editable, with dev extras)"
	@echo "  make ui        Build the web UI bundle (frontend/dist)"
	@echo "  make seed      Reset the DB and load sample data"
	@echo "  make serve     Run the API + web UI (http://127.0.0.1:8000)"
	@echo "  make demo      install + ui + seed + serve (one command)"
	@echo "  make test      Run the Python test suite"
	@echo "  make lint      Run ruff"
	@echo "  make clean     Remove the local database and UI build"

install:
	pip install -e ".[dev]"

ui:
	cd frontend && npm install && npm run build

seed:
	python -m src seed

sync:
	python -m src sync

serve:
	python -m src serve

run:
	python -m src run

test:
	pytest

lint:
	ruff check .

demo: install ui seed serve

clean:
	rm -f financial_os.db financial_os.db-shm financial_os.db-wal
	rm -rf frontend/dist
