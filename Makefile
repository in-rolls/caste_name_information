PY ?= .venv/bin/python
BLACK ?= .venv/bin/black
ISORT ?= .venv/bin/isort
FLAKE8 ?= .venv/bin/flake8
A01 := analyses/01_surname_to_category
A02 := analyses/02_jati_by_geography
A03 := analyses/03_how_few_names
A04 := analyses/04_which_token_is_the_surname
A05 := analyses/05_who_has_an_uninformative_name
A06 := analyses/06_neighbours
A07 := analyses/07_where_the_name_works
A08 := analyses/08_karnataka_psc
A09 := analyses/09_odisha_village_premium
A10 := analyses/10_kerala_psc
A11 := analyses/11_rajasthan_surname_to_category
A12 := analyses/12_rajasthan_land_village_premium

all: a01 a02 a03 a05 a06 a07 a08 a09 a10 a11 a12

a01:
	$(PY) $(A01)/pipeline.py
	$(PY) $(A01)/note.py

a02:
	$(PY) $(A02)/pipeline.py
	$(PY) $(A02)/note.py

test:
	$(PY) -m pytest -q

lint:
	$(BLACK) --check --fast src analyses tests
	$(ISORT) --check-only src analyses tests
	$(FLAKE8) src analyses tests

fmt:
	$(BLACK) --fast src analyses tests
	$(ISORT) src analyses tests

.PHONY: all app app-data a01 a02 a03 a04 a05 a06 a07 a08 a09 a10 a11 test lint fmt ci ci-docker

ci: lint test

ci-docker:
	docker run --rm -e DEBIAN_FRONTEND=noninteractive -e MPLCONFIGDIR=/tmp/matplotlib -e PIP_ROOT_USER_ACTION=ignore -v "$(PWD):/workspace" -w /workspace python:3.13-slim sh -c "apt-get update && apt-get install -y --no-install-recommends make && pip install -e '.[dev]' && make PY=python BLACK=black ISORT=isort FLAKE8=flake8 ci"

a03:
	$(PY) $(A03)/pipeline.py
	$(PY) $(A03)/note.py

a04:
	cd $(A04) && ../../$(PY) -m jupyter nbconvert --execute --inplace --to notebook investigate.ipynb

a05:
	$(PY) $(A05)/pipeline.py
	$(PY) $(A05)/note.py

a06:
	$(PY) $(A06)/pipeline.py
	$(PY) $(A06)/note.py

a07:
	$(PY) $(A07)/pipeline.py
	$(PY) $(A07)/note.py

a08:
	$(PY) $(A08)/pipeline.py
	$(PY) $(A08)/note.py

a09:
	$(PY) -m last_name_basis.land_records --states odisha

app-data:
	$(PY) $(A01)/pipeline.py

app:
	.venv/bin/streamlit run app/streamlit_app.py

a10:
	$(PY) $(A10)/pipeline.py
	$(PY) $(A10)/note.py

a11:
	$(PY) $(A11)/pipeline.py
	$(PY) $(A11)/note.py

.PHONY: a12 land-premium
a12:
	$(PY) -m last_name_basis.land_records --states rajasthan

land-premium:
	$(PY) -m last_name_basis.land_records
