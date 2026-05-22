# =============================================================================
# Global Variables
# =============================================================================
ROOT_DIR       := $(shell pwd)
SETTINGS       := cfg.settings
PORT           ?= 8000
ENV            ?= develop
GUNICORN_CONF  := build/gunicorn/conf.py
PYTHON_VERSION := $(shell python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Environment Control (Docker vs Local Virtualenv)
ifdef DOCKER
    PYTHON := python
    PIP    := pip
    CELERY := celery
else
    VENV   := $(CURDIR)/coes-env
    PYTHON := $(VENV)/bin/python
    PIP    := $(VENV)/bin/pip
    CELERY := $(VENV)/bin/celery
endif

MANAGE := $(PYTHON) manage.py

# =============================================================================
# Terminal Color Palette
# =============================================================================
RED    := \033[0;31m
YELLOW := \033[1;33m
GREEN  := \033[0;32m
NC     := \033[0m

# =============================================================================
# Phony Directives
# =============================================================================
.PHONY: help venv install-dev install-prod setup migrate superuser superuser-dev \
        run-dev run-prod shell celery celery-beat celery-flower lint format \
        docker-build docker-build-no-cache docker-up docker-up-build docker-down docker-logs \
        seed clean

# =============================================================================
# Help / Documentation
# =============================================================================
help:
	@echo "Commands available for CORE:"
	@echo "  make venv                     - Creates the virtual environment (skips if already exists)"
	@echo "  make install-dev              - Install development dependencies"
	@echo "  make install-prod             - Install production dependencies"
	@echo "  make run-dev                  - Start Django dev server"
	@echo "  make run-prod                 - Start production (gunicorn)"
	@echo "  make celery                   - Start Celery worker"
	@echo "  make celery-beat              - Start Celery Beat"
	@echo "  make celery-flower            - Start Celery Flower Dashboard"
	@echo "  make docker-up                - Start docker containers"
	@echo "  make docker-down              - Stop docker containers"
	@echo "  make shell                    - Opens the Django shell"
	@echo "  make lint                     - Runs ruff, pylint and mypy"
	@echo "  make format                   - Formats the code with Ruff"
	@echo "  make seed                     - Run seeds interactively"
	@echo "  make clean                    - Removes cache files safely"

# =============================================================================
# Virtual Environment Management
# =============================================================================
venv:
	@python3 -c "import venv" 2>/dev/null || { \
		echo "Error: 'python3-venv' is not installed for your environment."; \
		echo "Attempting to install system dependency for Python $(PYTHON_VERSION)..."; \
		sudo apt update && sudo apt install python3-venv -y; \
	}
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
		echo "Virtual environment created at $(VENV)"; \
	else \
		echo "Virtual environment already exists."; \
	fi

install-dev: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements/dev.txt

install-prod: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements/prod.txt

# =============================================================================
# Initial Configuration (Setup)
# =============================================================================
setup:
	@mkdir -p static staticfiles
	@printf "${GREEN}Directories ready${NC}\n"

# =============================================================================
# Database and Migrations
# =============================================================================
migrate:
	@printf "${YELLOW}Applying migrations ($(ENV))...${NC}\n"
	$(MANAGE) makemigrations --settings=$(SETTINGS).$(ENV) --noinput
	$(MANAGE) migrate --settings=$(SETTINGS).$(ENV) --noinput

superuser:
	$(MANAGE) createsuperuser --settings=$(SETTINGS).$(ENV)

superuser-dev:
	@printf "${YELLOW}Creating default dev superuser...${NC}\n"
	@DJANGO_SUPERUSER_PASSWORD=develop \
	DJANGO_SUPERUSER_USERNAME=develop \
	DJANGO_SUPERUSER_EMAIL=develop@coes.com \
	$(MANAGE) createsuperuser --noinput --settings=$(SETTINGS).$(ENV) || true

# =============================================================================
# Application Execution (Run)
# =============================================================================
run-dev: install-dev setup migrate superuser-dev
	@printf "${YELLOW}Using settings: $(SETTINGS).$(ENV)${NC}\n"
	@if [ -n "$$PYCHARM_DEBUG" ]; then \
		printf "${GREEN}Connecting to PyCharm debugger on port $$PYCHARM_PORT...${NC}\n"; \
		$(PYTHON) -c "import pydevd_pycharm; pydevd_pycharm.settrace('host.docker.internal', port=int('$$PYCHARM_PORT'), stdoutToServer=True, stderrToServer=True, suspend=False)"; \
	fi
	@printf "${GREEN}Starting Django on port $(PORT)...${NC}\n"
	$(MANAGE) runserver 0.0.0.0:$(PORT) --settings=$(SETTINGS).$(ENV)

run-prod: install-prod setup migrate
	@printf "${YELLOW}Collecting static files...${NC}\n"
	$(MANAGE) collectstatic --settings=$(SETTINGS).production --noinput
	@printf "${GREEN}Starting Gunicorn...${NC}\n"
	@DJANGO_SETTINGS_MODULE=$(SETTINGS).production \
	$(PYTHON) -m gunicorn -c $(GUNICORN_CONF) cfg.wsgi:application

# =============================================================================
# Celery Services
# =============================================================================
celery:
	DJANGO_SETTINGS_MODULE=$(SETTINGS).$(ENV) $(CELERY) -A cfg worker -l info

celery-beat:
	DJANGO_SETTINGS_MODULE=$(SETTINGS).$(ENV) $(CELERY) -A cfg beat -l info

celery-flower:
	@printf "${GREEN}Starting Flower on port 5555...${NC}\n"
	DJANGO_SETTINGS_MODULE=$(SETTINGS).$(ENV) \
	$(CELERY) -A cfg flower --port=5555 -l info


# =============================================================================
# Django Shell
# =============================================================================
shell:
	$(MANAGE) shell --settings=$(SETTINGS).$(ENV)

# =============================================================================
# Code Quality (Lint & Format)
# =============================================================================
lint:
	@printf "${YELLOW}Running Linters (Ruff, Pylint, Mypy)...${NC}\n"
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pylint cfg apps
	$(PYTHON) -m mypy .

format:
	@printf "${YELLOW}Formatting code with Ruff...${NC}\n"
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m ruff format .

# =============================================================================
# Docker Orchestration
# =============================================================================
docker-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build

docker-build-no-cache:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache --pull

docker-up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

docker-up-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# =============================================================================
# Test Data (Seeds)
# =============================================================================

test:
	DJANGO_SETTINGS_MODULE=cfg.settings.testing pytest


NUMBER ?= 10

seed:
	@printf "${YELLOW}Select seed to run:${NC}\n"
	@printf "  1) users\n"
	@printf "  0) all\n"
	@printf "${GREEN}Enter option: ${NC}"; \
	read option; \
	printf "${GREEN}Enter number of records: ${NC}"; \
	read num; \
	count=$${num:-$(NUMBER)}; \
	case $$option in \
		1) $(MANAGE) seed_users --number=$$count --settings=$(SETTINGS).$(ENV);; \
		0) $(MANAGE) seed_users --number=$$count --settings=$(SETTINGS).$(ENV);; \
		*) printf "${RED}Invalid option${NC}\n";; \
	esac

# =============================================================================
# Workspace Cleanup
# =============================================================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	find . -path "*/migrations/*.pyc" -delete
	@printf "${RED}Note: Cache cleaned. Migrations were NOT deleted for safety.${NC}\n"