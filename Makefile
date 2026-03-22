.PHONY: dev up down logs test migrate build clean help

# ─── 本地开发 ─────────────────────────────────────────────────
dev: ## 本地开发（前后端热重载，需先启动 Redis）
	@echo "启动后端 + Celery worker + 前端..."
	@trap 'kill 0' EXIT; \
	cd src && uvicorn server.main:app --reload --port 8000 & \
	celery -A server.tasks.celery_app worker --loglevel=info --concurrency=2 & \
	cd web && npm run dev & \
	wait

dev-redis: ## 用 Docker 启动 Redis（本地开发依赖）
	docker run -d --name wt-redis -p 6379:6379 redis:7-alpine

# ─── Docker Compose ───────────────────────────────────────────
up: ## 一键启动所有服务
	docker compose up -d --build

down: ## 停止所有服务
	docker compose down

logs: ## 查看所有服务日志
	docker compose logs -f

logs-backend: ## 仅查看后端日志
	docker compose logs -f backend worker

logs-frontend: ## 仅查看前端日志
	docker compose logs -f frontend

restart: ## 重启所有服务
	docker compose restart

# ─── 测试 ─────────────────────────────────────────────────────
test: ## 运行所有测试
	PYTHONPATH=src pytest tests/ -v

test-cov: ## 运行测试（含覆盖率）
	PYTHONPATH=src pytest tests/ -v --cov=src --cov-report=term-missing

# ─── 数据库 ───────────────────────────────────────────────────
migrate: ## 运行数据库迁移
	cd src && alembic -c ../alembic.ini upgrade head

migrate-new: ## 创建新迁移（用法: make migrate-new MSG="add xxx")
	cd src && alembic -c ../alembic.ini revision --autogenerate -m "$(MSG)"

# ─── 构建 ─────────────────────────────────────────────────────
build: ## 构建前端
	cd web && npm run build

build-docker: ## 仅构建 Docker 镜像（不启动）
	docker compose build

# ─── 清理 ─────────────────────────────────────────────────────
clean: ## 清理构建产物和缓存
	rm -rf web/dist build/ dist/ *.egg-info .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-docker: ## 清理 Docker 容器、镜像和 volume
	docker compose down -v --rmi local

# ─── 帮助 ─────────────────────────────────────────────────────
help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
