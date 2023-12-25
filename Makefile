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
build: build ## Build the container in case you made changes
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

.PHONY: test
test: poetry-install ## run pytest
	@docker compose exec testing poetry run pytest

.PHONY: shell
shell: poetry-install ## run shell
	@docker compose exec testing bash -c "SHELL=bash poetry shell"

.PHONY: entr
entr: poetry-install ## run entr
	@docker compose exec testing bash -c "find -name '*.py' | SHELL=bash poetry run entr bash -c 'pytest -x --lf'"
