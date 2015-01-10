REBUILD_FLAG =
VENV=env
BIN=$(VENV)/bin
ACTIVATE=source $(BIN)/activate

.PHONY: all
all: test build pre-commit

.PHONY: pre-commit
pre-commit: .git/hooks/pre-commit
.git/hooks/pre-commit: .pre-commit-config.yaml $(VENV)
	$(ACTIVATE); pre-commit install

$(VENV): $(VENV)/bin/activate

$(VENV)/bin/activate: requirements-dev.txt
	test -d $(VENV) || virtualenv -p /usr/bin/python3 --system-site-packages $(VENV)
	$(ACTIVATE); pip install -r requirements-dev.txt
	touch $(BIN)/activate


.PHONY: test
test: $(VENV)
	$(ACTIVATE); tox $(REBUILD_FLAG)

dist/*.whl: setup.py rawphoto/*.py
	python setup.py sdist bdist_wheel

dist/*.tar.gz: setup.py rawphoto/*.py
	python setup.py sdist bdist_wheel

.PHONY: wheel
wheel: dist/*.whl

.PHONY: sdist
sdist: dist/*.tar.gz

.PHONY: build
build: pre-commit wheel sdist

.PHONY: clean
clean:
	find . -iname '*.pyc' | xargs rm -f
	rm -rf .tox
	rm -rf $(VENV)

.PHONY: upload
upload: build test
	python setup.py sdist bdist_wheel upload
