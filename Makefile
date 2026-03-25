PYTHON ?= python3
PORT ?= 7860

.PHONY: install run test smoke validate baseline

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	uvicorn app.server:app --host 0.0.0.0 --port $(PORT)

test:
	$(PYTHON) -m pytest -q

smoke:
	$(PYTHON) scripts/smoke_test.py

validate:
	openenv validate

baseline:
	$(PYTHON) -m app.baseline --model $${OPENAI_MODEL:-gpt-4.1-mini}

