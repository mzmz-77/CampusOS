.PHONY: setup dev test build
setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install --cache-dir work/pip-cache -r backend/requirements.txt
	cd frontend && npm ci --cache ../work/npm-cache
dev:
	python3 scripts/dev.py
test:
	cd backend && ../.venv/bin/python -m pytest -q
	cd frontend && npm test
build:
	cd frontend && npm run build
