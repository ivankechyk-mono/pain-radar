PYTHON=.venv/bin/python3.12

.PHONY: install migrate collect classify dashboard

install:
	python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt

migrate:
	$(PYTHON) scripts/run_migrate.py

collect:
	$(PYTHON) scripts/run_collect.py

classify:
	$(PYTHON) scripts/run_classify.py

dashboard:
	.venv/bin/streamlit run dashboard.py
