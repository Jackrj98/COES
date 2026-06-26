# =============================================================================
# Global Variables
# =============================================================================
NUMBER 		   ?= 10
ROOT_DIR       := $(shell pwd)
SETTINGS       := cfg.settings
PORT           ?= 8005
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
        seed clean translate-generate translate-compile \
        docker-prod-build docker-prod-build-no-cache docker-prod-up docker-prod-down docker-prod-restart \
        dev-up dev-down dev-logs prod-up prod-down prod-logs

# =============================================================================
# Help / Documentation
# =============================================================================
help:
	@echo "Commands available for COES:"
	@echo ""
	@echo "  Environment:"
	@echo "  make venv                     - Creates the virtual environment"
	@echo "  make install-dev              - Install development dependencies"
	@echo "  make install-prod             - Install production dependencies"
	@echo ""
	@echo "  Run:"
	@echo "  make run-dev                  - Start Django dev server (port $(PORT))"
	@echo "  make run-prod                 - Start production (gunicorn)"
	@echo "  make celery                   - Start Celery worker"
	@echo "  make celery-beat              - Start Celery Beat"
	@echo "  make celery-flower            - Start Celery Flower Dashboard"
	@echo "  make shell                    - Opens the Django shell"
	@echo ""
	@echo "  Docker Development:"
	@echo "  make dev-up                   - Start development containers"
	@echo "  make dev-down                 - Stop development containers"
	@echo "  make dev-logs                 - View development logs"
	@echo "  make dev-shell                - Enter web container"
	@echo ""
	@echo "  Docker Production:"
	@echo "  make prod-up                  - Start production containers"
	@echo "  make prod-down                - Stop production containers"
	@echo "  make prod-logs                - View production logs"
	@echo "  make prod-shell               - Enter web container"
	@echo ""
	@echo "  Database:"
	@echo "  make migrate                  - Run migrations"
	@echo "  make superuser                - Create superuser"
	@echo "  make seed                     - Run seeds interactively"
	@echo ""
	@echo "  Code Quality:"
	@echo "  make lint                     - Runs ruff, pylint and mypy"
	@echo "  make format                   - Formats the code with Ruff"
	@echo ""
	@echo "  Clean:"
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
	@echo "Development dependencies installed"

install-prod: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements/prod.txt
	@echo "Production dependencies installed"

# =============================================================================
# Initial Configuration (Setup)
# =============================================================================
setup:
	@mkdir -p static staticfiles
	@mkdir -p /var/log/gunicorn /var/log/nginx 2>/dev/null || true
	@printf "${GREEN} Directories ready${NC}\n"

# =============================================================================
# Database and Migrations
# =============================================================================
migrate:
	@printf "${YELLOW} Applying migrations ($(ENV))...${NC}\n"
	$(MANAGE) wait_for_db --settings=$(SETTINGS).$(ENV)
	$(MANAGE) makemigrations --settings=$(SETTINGS).$(ENV) --noinput
	$(MANAGE) migrate --settings=$(SETTINGS).$(ENV) --noinput
	@printf "${GREEN} Migrations applied${NC}\n"

superuser:
	$(MANAGE) createsuperuser --settings=$(SETTINGS).$(ENV)

superuser-dev:
	@printf "${YELLOW}Creating default dev superuser...${NC}\n"
	@DJANGO_SUPERUSER_PASSWORD=develop \
	DJANGO_SUPERUSER_USERNAME=develop \
	DJANGO_SUPERUSER_EMAIL=develop@coes.com \
	$(MANAGE) createsuperuser --noinput --settings=$(SETTINGS).$(ENV) || true
	@printf "${GREEN} Default superuser created (user: develop, pass: develop)${NC}\n"

# =============================================================================
# Application Execution (Run)
# =============================================================================
run-dev: setup migrate superuser-dev translate-compile
	@printf "${YELLOW}Using settings: $(SETTINGS).$(ENV)${NC}\n"
	@printf "${GREEN} Starting Django on port $(PORT)...${NC}\n"
	$(MANAGE) runserver 0.0.0.0:$(PORT) --settings=$(SETTINGS).$(ENV)

run-prod: setup migrate superuser-dev translate-compile
	@printf "${YELLOW} Collecting static files...${NC}\n"
	$(MANAGE) collectstatic --settings=$(SETTINGS).production --noinput
	@printf "${YELLOW} Starting Gunicorn...${NC}\n"
	@mkdir -p /var/log/gunicorn 2>/dev/null || true
	@DJANGO_SETTINGS_MODULE=$(SETTINGS).production \
	$(PYTHON) -m gunicorn -c $(GUNICORN_CONF) cfg.wsgi:application

# =============================================================================
# Celery Services
# =============================================================================
celery:
	@printf "${YELLOW} Starting Celery worker...${NC}\n"
	$(MANAGE) wait_for_db --settings=$(SETTINGS).$(ENV)
	DJANGO_SETTINGS_MODULE=$(SETTINGS).$(ENV) $(CELERY) -A cfg worker -l info

celery-beat:
	@printf "${YELLOW} Starting Celery Beat...${NC}\n"
	$(MANAGE) wait_for_db --settings=$(SETTINGS).$(ENV)
	DJANGO_SETTINGS_MODULE=$(SETTINGS).$(ENV) $(CELERY) -A cfg beat -l info

celery-flower:
	@printf "${YELLOW} Starting Flower on port 5555...${NC}\n"
	$(MANAGE) wait_for_db --settings=$(SETTINGS).$(ENV)
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
	@printf "${YELLOW} Running Linters (Ruff, Pylint, Mypy)...${NC}\n"
	$(PYTHON) -m ruff check .
	$(PYTHON) -m pylint cfg apps
	$(PYTHON) -m mypy .
	@printf "${GREEN}Linting complete${NC}\n"

format:
	@printf "${YELLOW} Formatting code with Ruff...${NC}\n"
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m ruff format .
	@printf "${GREEN}Formatting complete${NC}\n"

# =============================================================================
# Docker Development
# =============================================================================
dev-up:
	@printf "${GREEN} Starting development containers...${NC}\n"
	docker compose -f docker-compose.dev.yml up
	@printf "${GREEN}Development environment ready${NC}\n"
	@printf "Web: http://localhost:$(PORT)\n"
	@printf "Mailhog: http://localhost:8026\n"
	@printf "Flower: http://localhost:5555\n"

dev-down:
	@printf "${YELLOW} Stopping development containers...${NC}\n"
	docker compose -f docker-compose.dev.yml down
	@printf "${GREEN}Development containers stopped${NC}\n"

dev-logs:
	docker compose -f docker-compose.dev.yml logs -f

dev-shell:
	docker compose -f docker-compose.dev.yml exec web bash

dev-rebuild:
	@printf "${YELLOW} Rebuilding development containers...${NC}\n"
	docker compose -f docker-compose.dev.yml up -d --build
	@printf "${GREEN}Development containers rebuilt${NC}\n"

dev-rebuild-no-cache:
	@printf "${YELLOW} Rebuilding development containers (no cache)...${NC}\n"
	docker compose -f docker-compose.dev.yml build --no-cache
	docker compose -f docker-compose.dev.yml up -d
	@printf "${GREEN} Development containers rebuilt (no cache)${NC}\n"

# =============================================================================
# Docker Production
# =============================================================================
prod-up:
	@printf "${GREEN} Starting production containers...${NC}\n"
	docker compose -f docker-compose.yml up -d
	@printf "${GREEN}Production environment ready${NC}\n"
	docker compose -f docker-compose.yml ps

prod-down:
	@printf "${YELLOW} Stopping production containers...${NC}\n"
	docker compose -f docker-compose.yml down
	@printf "${GREEN}Production containers stopped${NC}\n"

prod-logs:
	docker compose -f docker-compose.yml logs -f

prod-shell:
	docker compose -f docker-compose.yml exec web bash

prod-rebuild:
	@printf "${YELLOW} Rebuilding production containers...${NC}\n"
	docker compose -f docker-compose.yml up -d --build
	@printf "${GREEN}Production containers rebuilt${NC}\n"

# =============================================================================
# Docker Legacy (Backward Compatibility)
# =============================================================================
docker-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build
	@echo "This is legacy. Use 'make dev-up' for development"

docker-build-no-cache:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache --pull
	@echo "This is legacy. Use 'make dev-rebuild' for development"

docker-up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up
	@echo "This is legacy. Use 'make dev-up' for development"

docker-up-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
	@echo "This is legacy. Use 'make dev-rebuild' for development"

docker-down:
	docker compose down
	@echo "This is legacy. Use 'make dev-down' for development"

docker-logs:
	docker compose logs -f
	@echo "This is legacy. Use 'make dev-logs' for development"

docker-prod-build:
	docker compose -f docker-compose.yml build
	@echo "This is legacy. Use 'make prod-rebuild' for production"

docker-prod-build-no-cache:
	docker compose -f docker-compose.yml build --no-cache
	@echo "This is legacy. Use 'make prod-rebuild' for production"

docker-prod-up:
	@printf "${GREEN} Starting production containers...${NC}\n"
	docker compose -f docker-compose.yml up -d --force-recreate --remove-orphans
	@printf "${GREEN}Production containers started${NC}\n"
	docker compose -f docker-compose.yml ps

docker-prod-down:
	@printf "${YELLOW} Stopping production containers...${NC}\n"
	docker compose -f docker-compose.yml down
	@printf "${GREEN}Production containers stopped${NC}\n"

docker-prod-restart:
	@printf "${YELLOW} Restarting production containers...${NC}\n"
	docker compose -f docker-compose.yml restart
	@printf "${GREEN}Production containers restarted${NC}\n"

# =============================================================================
# Test Data (Seeds)
# =============================================================================
test:
	DJANGO_SETTINGS_MODULE=cfg.settings.testing pytest --spec

test-report:
	DJANGO_SETTINGS_MODULE=cfg.settings.testing pytest --html=report.html --self-contained-html

seed:
	@printf "${YELLOW}Select seed to run:${NC}\n"
	@printf "  1) users\n"
	@printf "  2) suppliers\n"
	@printf "  3) catalogs\n"
	@printf "  4) inventory\n"
	@printf "  0) all\n"
	@printf "${GREEN}Enter option: ${NC}"
	@read option; \
	printf "${GREEN}Enter number of records: ${NC}"; \
	read num; \
	count=$${num:-$(NUMBER)}; \
	case $$option in \
		1) $(MANAGE) seed_users --number=$$count --settings=$(SETTINGS).$(ENV) ;; \
		2) $(MANAGE) seed_suppliers --number=$$count --settings=$(SETTINGS).$(ENV) ;; \
		3) $(MANAGE) seed_catalogs --settings=$(SETTINGS).$(ENV) ;; \
		4) $(MANAGE) seed_inventory --number=$$count --settings=$(SETTINGS).$(ENV) ;; \
		0) \
			$(MANAGE) seed_catalogs --settings=$(SETTINGS).$(ENV); \
			$(MANAGE) seed_users --number=$$count --settings=$(SETTINGS).$(ENV); \
			$(MANAGE) seed_suppliers --number=$$count --settings=$(SETTINGS).$(ENV); \
			$(MANAGE) seed_inventory --number=$$count --settings=$(SETTINGS).$(ENV);; \
		*) printf "${RED} Invalid option${NC}\n" ;; \
	esac

# =============================================================================
# Workspace Cleanup
# =============================================================================
clean:
	@printf "${YELLOW} Cleaning cache files...${NC}\n"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@printf "${GREEN}Cache cleaned${NC}\n"

clean-all: clean
	@printf "${YELLOW} Cleaning migrations...${NC}\n"
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 2>/dev/null || true
	find . -path "*/migrations/*.pyc" -delete 2>/dev/null || true
	@printf "${GREEN}All cleaned${NC}\n"

# =============================================================================
# Translations
# =============================================================================
translate-generate:
	@printf "${YELLOW} Generating translation files...${NC}\n"
	$(MANAGE) makemessages -l es --ignore="coes-env/*"
	@printf "${GREEN}Translations generated${NC}\n"

translate-compile:
	@printf "${YELLOW} Compiling translations...${NC}\n"
	$(MANAGE) compilemessages -v 0
	@printf "${GREEN}Translations compiled${NC}\n"