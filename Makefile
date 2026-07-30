# Pardachi — tez-tez ishlatiladigan buyruqlar
.DEFAULT_GOAL := help
.PHONY: help setup up down logs restart build migrate seed reset-db test lint backend frontend tunnel status

help: ## Buyruqlar ro'yxati
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## .env faylini yaratish va kalit generatsiya qilish
	@test -f .env || cp .env.example .env
	@python3 -c "import re,pathlib,secrets; p=pathlib.Path('.env'); s=p.read_text(); s=re.sub(r'^SECRET_KEY=.*$$','SECRET_KEY='+secrets.token_hex(32),s,flags=re.M); p.write_text(s)"
	@echo ".env tayyor. TELEGRAM_BOT_TOKEN va ADMIN_TELEGRAM_IDS ni to'ldiring."

tunnel: ## Mini App'ni internetga chiqarish (tunnel + .env + bot)
	./scripts/tunnel.sh

status: ## Servislar va tunnel holatini ko'rish
	@docker compose ps --format 'table {{.Name}}\t{{.Status}}'
	@printf '\nTunnel: '
	@pgrep -f 'cloudflared tunnel' >/dev/null && grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/pardachi-cloudflared.log | head -1 || echo "ishlamayapti (make tunnel)"
	@printf 'WEBAPP_URL: '; grep '^WEBAPP_URL=' .env | cut -d= -f2-

up: ## Barcha servislarni ishga tushirish
	docker compose up -d --build

down: ## Servislarni to'xtatish
	docker compose down

logs: ## Loglarni kuzatish
	docker compose logs -f --tail=100

restart: ## Qayta ishga tushirish
	docker compose restart

build: ## Tasvirlarni qayta yig'ish
	docker compose build --no-cache

migrate: ## Migratsiyalarni qo'llash
	docker compose exec backend alembic upgrade head

seed: ## Namunaviy ma'lumotlarni yuklash
	docker compose exec backend python -m scripts.seed

reset-db: ## Bazani tozalab, namunaviy ma'lumot yuklash
	docker compose exec backend python -m scripts.seed --reset

test: ## Backend testlari
	cd backend && .venv/bin/python -m pytest -q

lint: ## Kod tekshiruvi
	cd backend && .venv/bin/ruff check app tests scripts
	cd frontend && npm run typecheck

backend: ## Backendni lokal ishga tushirish
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

frontend: ## Front-endni lokal ishga tushirish
	cd frontend && npm run dev
