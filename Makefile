.DEFAULT_GOAL := help

CACHE_IMG = "ghcr.io/adfinis/pyaptly/cache:latest"

DOCKER_BUILDKIT = 1
export DOCKER_BUILDKIT

# Help target extracts the double-hash comments from the targets and shows them
# in a convenient way. This allows us to easily document the user-facing Make
# targets
.PHONY: help
help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort -k 1,1 | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Build the container in case you made changes
	@docker compose build

.PHONY: up
up: ## start the container (cached)
	@docker compose up -d

.PHONY: push
push: ## push docker image cache to the registry
	@docker push $(CACHE_IMG)

.PHONY: down
down: ## stop and remove container 
	@docker compose down -v

.PHONY: recreate
recreate: down up ## recreate container

.PHONY: wait-for-ready
wait-for-ready: up ## wait for web-server to be ready for testing
	@docker compose exec testing wait-for-it -t 0 127.0.0.1:3123
	@docker compose exec testing wait-for-it -t 0 127.0.0.1:8080

.PHONY: poetry-install
poetry-install: wait-for-ready ## install dev environment
	@docker compose exec testing poetry install --without lsp

.PHONY: mypy
mypy: poetry-install
	@docker compose exec testing poetry run dmypy run -- pyaptly

.PHONY: pytest
pytest: poetry-install ## run pytest
	@docker compose exec testing poetry run sh -c "HYPOTHESIS_PROFILE=$(HYPOTHESIS_PROFILE) pytest -vv --cov"

.PHONY: format
format: poetry-install ## format code with ruff
	@docker compose exec testing poetry run ruff format pyaptly

.PHONY: fix
fix: poetry-install ## fix code with ruff
	@docker compose exec testing poetry run ruff check --fix pyaptly

.PHONY: lint-code
lint-code:  ## check all linters
	@docker compose exec testing poetry run ruff check pyaptly

.PHONY: test
test: pytest mypy lint-code ## run all testing


.PHONY: docs
docs: poetry-install ## generate documentation
	rm -vrf docs/_build/* docs/cli/*
	[[ -d docs/sphinx-template ]] || git clone https://github.com/adfinis-sygroup/adsy-sphinx-template docs/sphinx-template
	@docker compose exec testing bash -c "poetry install --only docs"
	
	# Currently md-click has a bad dependency on old click. We fix this with the next command
	@docker compose exec testing bash -c "poetry run pip install md-click==1.0.1"
	@docker compose exec testing bash -c "patch -f /root/.cache/pypoetry/virtualenvs/pyaptly-*-py3.11/lib/python3.11/site-packages/md_click/main.py md-click.patch || true"
	
	# Generate CLI & Config docs
	@docker compose exec testing bash -c "mkdir -p docs/_temp && poetry run mdclick dumps --baseModule=pyaptly.cli --baseCommand=pyaptly --docsPath=./docs/_temp"
	@docker compose exec testing bash -c "poetry run jsonschema2md pyaptly/config.schema.json docs/Config_Reference.md"
	
	@cat docs/_temp/pyaptly.md docs/_temp/pyaptly-*.md > docs/Command_Line_Reference.md
	# mdclick has not enough indentation
	@sed -i 's/^#/##/' docs/Command_Line_Reference.md
	# Add title, must happen after the above sed command
	@sed -i '1a<!-- This file is generated with mdclick -->\n# Command Line Reference' docs/Command_Line_Reference.md
	@docker compose exec testing bash -c "rm -r docs/_temp"
	
	# SPHINX Render
	@docker compose exec testing bash -c 'cd docs/ && poetry run make html'

.PHONY: shell
shell: poetry-install ## run shell
	@docker compose exec testing bash -c "SHELL=bash poetry shell"

.PHONY: entr-pytest
entr-pytest: poetry-install ## run pytest with entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'pytest -x --lf; echo ---'"

.PHONY: entr-mypy
entr-mypy: poetry-install ## run pytest with entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'make local-mypy; echo ---'"

.PHONY: entr-lint
entr-lint: poetry-install ## run ruff with entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'ruff check pyaptly; echo ---'"

.PHONY: local-mypy
local-mypy: ## Run mypy as daemon locally (requires local-dev)
	@poetry run dmypy run -- pyaptly

.PHONY: build-packages
build-packages: poetry-install ## build source package, wheel and srpm
	@docker compose exec testing bash -c "poetry run ./tools/build-rpm"

.PHONY: rebuild-packages
rebuild-packages: ## build binary rpms
	@docker run -v ./:/source rockylinux:9 sh -c "dnf install -y git; git config --global --add safe.directory /source; /source/tools/venv-rpm"
	@docker run -v ./:/source fedora:39 /source/tools/rebuild-rpm
	@docker run -v ./:/source fedora:40 /source/tools/rebuild-rpm
