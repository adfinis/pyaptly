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
	@docker compose exec testing poetry install

.PHONY: mypy
mypy: poetry-install
	@docker compose exec testing poetry run dmypy run -- pyaptly

.PHONY: pytest
pytest: poetry-install ## run pytest
	@docker compose exec testing poetry run pytest -vv --cov

.PHONY: check-isort
check-isort: poetry-install ## check isort
	@docker compose exec testing poetry run isort --check pyaptly

.PHONY: check-black
check-black: poetry-install ## check black
	@docker compose exec testing poetry run black --check pyaptly

.PHONY: check-black
format-black: poetry-install ## format code with black
	@docker compose exec testing poetry run black pyaptly

.PHONY: flake8
flake8: poetry-install ## run flake8
	@docker compose exec testing poetry run flake8 pyaptly

.PHONY: lint-code
lint-code: check-isort check-black flake8 ## check all linters

.PHONY: test
test: pytest mypy lint-code ## run all testing

.PHONY: shell
shell: poetry-install ## run shell
	@docker compose exec testing bash -c "SHELL=bash poetry shell"

.PHONY: entr-pytest
entr-pytest: poetry-install ## run pytest with entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'pytest -x --lf; echo ---'"

.PHONY: entr-mypy
entr-mypy: poetry-install ## run pytest with entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'make local-mypy; echo ---'"

.PHONY: entr-flake8
entr-flake8: poetry-install ## run flake8 with entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'flake8 pyaptly; echo ---'"

.PHONY: local-mypy
local-mypy: ## Run mypy as daemon locally (requires local-dev)
	@poetry run dmypy run -- pyaptly

.PHONY: build-packages
build-packages: poetry-install ## build source package, wheel and srpm
	@docker compose exec testing bash -c "poetry run ./tools/build-rpm"

.PHONY: rebuild-packages
rebuild-packages: ## build binary rpms
	@docker run -v ./:/source rockylinux:9 /source/tools/venv-rpm
	@docker run -v ./:/source fedora:39 /source/tools/rebuild-rpm
	@docker run -v ./:/source fedora:40 /source/tools/rebuild-rpm
