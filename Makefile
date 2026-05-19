# =============================================================================
# CauSium — Operational Makefile
#
# Provides convenient targets for backup, restore, DR drills, and dev setup.
# All targets are safe to run locally; production operations should be
# executed with appropriate environment variables set.
#
# Usage:
#   make backup              # Full backup of all datastores
#   make restore BACKUP=...  # Restore from a specific backup directory
#   make dr-drill            # Full RTO/RPO drill (backup + restore + verify)
#   make dr-drill-dry        # Backup only (no restore)
#   make dev-up              # Start all services for development
#   make dev-down            # Stop all services
# =============================================================================

.PHONY: help backup restore dr-drill dr-drill-dry verify-backup dev-up dev-down dev-reset health

SHELL := /bin/bash
BACKUP ?= $(shell ls -td backups/*/ 2>/dev/null | head -1)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Backup & Restore
# ---------------------------------------------------------------------------

backup: ## Take a full backup (PostgreSQL + ClickHouse + Redis)
	@echo "==> Starting full backup..."
	@bash scripts/backup.sh

restore: ## Restore from BACKUP directory (e.g., make restore BACKUP=backups/2026-01-01_120000)
	@if [ -z "$(BACKUP)" ]; then \
		echo "ERROR: No backup directory specified. Usage: make restore BACKUP=backups/<timestamp>"; \
		exit 1; \
	fi
	@echo "==> Restoring from: $(BACKUP)"
	@bash scripts/restore.sh "$(BACKUP)"

verify-backup: ## Verify the latest backup can be listed and has expected structure
	@if [ -z "$(BACKUP)" ]; then \
		echo "ERROR: No backup found in backups/. Run 'make backup' first."; \
		exit 1; \
	fi
	@echo "==> Verifying backup: $(BACKUP)"
	@echo "  Checking PostgreSQL dump..."
	@test -f "$(BACKUP)/postgres/"*.dump && echo "    ✓ PostgreSQL dump found" || echo "    ✗ PostgreSQL dump MISSING"
	@echo "  Checking ClickHouse tables..."
	@ls "$(BACKUP)/clickhouse/"*.bin >/dev/null 2>&1 && echo "    ✓ ClickHouse binaries found" || echo "    ✗ ClickHouse binaries MISSING"
	@echo "  Checking Redis RDB..."
	@test -f "$(BACKUP)/redis/dump.rdb" && echo "    ✓ Redis RDB found" || echo "    ✗ Redis RDB MISSING"
	@echo "  Checking backup report..."
	@test -f "$(BACKUP)/backup_report.json" && echo "    ✓ Backup report found" || echo "    ✗ Backup report MISSING"

# ---------------------------------------------------------------------------
# DR Drills
# ---------------------------------------------------------------------------

dr-drill: ## Full disaster recovery drill (backup → restore → verify → report)
	@echo "==> Starting full DR drill..."
	@bash scripts/rto_rpo_test.sh

dr-drill-dry: ## DR drill dry-run (backup only, no restore)
	@echo "==> Starting DR drill (dry-run)..."
	@DRY_RUN=true bash scripts/rto_rpo_test.sh

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

dev-up: ## Start all services (docker compose up)
	docker compose up -d
	@echo "==> Services starting. Run 'make health' to check status."

dev-down: ## Stop all services
	docker compose down

dev-reset: ## Stop services and remove volumes (DESTRUCTIVE)
	@echo "WARNING: This will delete all local data volumes."
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose down -v

health: ## Check health of all services
	@echo "==> Service health:"
	@docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
		docker compose ps
	@echo ""
	@echo "==> Backend health endpoint:"
	@curl -sf http://localhost:8000/health 2>/dev/null | python3 -m json.tool 2>/dev/null || \
		echo "  Backend not reachable (is it running?)"
