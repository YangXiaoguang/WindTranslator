# 2026-3-20
> 对项目进行全面重构，使之加结构化系统化，增加可扩展性，可维护性
## 新结构（22个文件）：

```
src/epub_translator/
├── cli.py            ← argparse + main()，只管参数和组装
├── config.py         ← TranslatorConfig、load_config()、所有常量
├── models.py         ← ContentBlock、Chapter（纯数据）
├── pipeline.py       ← TranslationPipeline，编排 parse→translate→render
├── parser/
│   ├── base.py       ← AbstractParser（接口）
│   └── epub.py       ← EPUBParser（实现）
├── translator/
│   ├── llm.py        ← LLMTranslator：批量/重试/缓存逻辑
│   ├── cache.py      ← SQLite缓存，key=sha256(provider:model:text)
│   └── providers/
│       ├── base.py          ← LLMProvider ABC
│       ├── anthropic.py     ← AnthropicProvider
│       ├── openai_compat.py ← OpenAI/DeepSeek/Custom
│       └── __init__.py      ← get_provider(cfg) 工厂函数
├── renderer/
│   ├── base.py       ← AbstractRenderer（接口）
│   ├── styles.py     ← 字体注册 + 样式定义
│   └── pdf.py        ← PDFRenderer（实现）
└── utils/
    └── chapter_range.py ← parse_chapter_range()
```

## 关键改动与收益：

| 问题	| 解决方案 | 
| :--- | :--- |
| if/else provider 分发	| LLMProvider ABC + get_provider() 工厂，加新 provider 只需一个文件 | 
| 中断后从头重翻	|  SQLite 缓存，key 含 model+provider，换模型自动失效 | 
| print 散落全局 | 	logging 模块，统一格式，未来可接文件/结构化日志 | 
| system_prompt 硬编码路径	|  配置项 system_prompt_path，同 translator.yaml 逻辑搜索，找不到降级内置 | 
| --no-cache	|  新增 CLI flag，cache_enabled=False 跳过全部缓存 | 

## 使用方式：

```
pip install -e .          # 安装（editable 模式）
epub-translator book.epub # 或
python -m epub_translator book.epub
```
运行测试：

```
pip install -e ".[dev]"
pytest tests/
```

---

新增文件 (26 个)
数据模型 (4 个)

project.py — TranslationProject 表（书名、状态、文件路径）
chapter.py — Chapter 表（序号、标题、状态）
content_block.py — ContentBlock 表（block_type、原文、译文、状态）
translation_config.py — TranslationConfig 表（provider、model、加密 API key）
Repository 层 (4 个)

project_repo.py — CRUD + 状态更新
chapter_repo.py — 按项目查询 + eager-load blocks
block_repo.py — 批量创建/更新翻译 + 按状态查询
config_repo.py — 配置管理 + 默认配置查询
解析器

parser/epub.py — 复用引擎 EPUBParser，解析后写入 DB
翻译引擎

providers/base.py — BaseLLMProvider 抽象基类
providers/anthropic.py — Anthropic Claude 实现
providers/openai_compat.py — OpenAI 兼容实现
engine.py — 从 DB 读取 → 批量翻译 → 写回 DB + 进度回调
PDF 渲染器

renderer/pdf.py — 从 DB 读取已翻译内容 → 生成 PDF
基础设施

config.py — Pydantic Settings (env vars)
database.py — async SQLAlchemy engine + session factory
crypto.py — Fernet 加密/解密 API key
tasks/celery_app.py — Celery 实例
tasks/translate.py — translate_book Celery 任务
ws/manager.py — WebSocket 连接管理器
测试 (2 个)

test_parser.py — 8 个测试：解析写 DB、章节/块验证、异常处理
test_translator.py — 7 个测试：翻译全流程、batch/fallback、中断恢复、进度回调
脚本

translate_cli.py — 端到端 CLI，parse → translate → render
验收结果
| 验收项 | 状态  |
|----|----|
| alembic upgrade head	4 | 张表创建成功 | 
| pytest tests/server/test_parser.py	| 8/8 passed | 
| pytest tests/server/test_translator.py | 	7/7 passed | 
| 全量测试 (含原有 42 个)	| 57/57 passed | 
| scripts/translate_cli.py	| 已就绪（需 API key 端到端运行） | 

---
实现总结
新增文件 (16 个)
FastAPI 应用

main.py — App 工厂, CORS, 生命周期, 路由挂载
dependencies.py — DB session 依赖注入
storage.py — 上传/输出文件管理 (50MB 限制, 项目清理)
中间件

error_handler.py — 全局异常 → 统一 JSON 错误
request_log.py — 请求日志 (method, path, status, duration)
路由 (4 个)

projects.py — POST /upload, GET /, GET /{id}, DELETE /{id}
translate.py — POST /{id}/translate, POST /{id}/cancel, GET /{id}/progress
downloads.py — GET /{id}/download/pdf
config.py — GET /providers, POST /test-key
Schemas

common.py — ApiResponse, ok(), fail() 统一响应
translate.py — TranslateRequest, ProgressResponse, TestKeyRequest
Celery + WebSocket

tasks/translate.py — 重构: 接收直接参数 + Redis pub/sub 进度推送
ws/progress.py — WS /ws/projects/{id}/progress, Redis 订阅 → WebSocket 转发 + DB 轮询降级
Docker

docker-compose.yml — redis + api + worker 三服务编排
docker/Dockerfile.api — Python 3.11 镜像
.env.example — 环境变量模板
测试

test_api.py — 9 个 API 端点测试 (httpx AsyncClient)
API 端点清单 (10 个路径)
Method	Path	功能
GET	/api/health	健康检查
POST	/api/projects/upload	上传电子书
GET	/api/projects	项目列表
GET	/api/projects/{id}	项目详情 + 章节
DELETE	/api/projects/{id}	删除项目
POST	/api/projects/{id}/translate	触发翻译
POST	/api/projects/{id}/cancel	取消翻译
GET	/api/projects/{id}/progress	轮询进度
GET	/api/projects/{id}/download/pdf	下载 PDF
GET	/api/config/providers	Provider 列表
POST	/api/config/test-key	测试 API Key
WS	/ws/projects/{id}/progress	实时进度推送
验收结果
验收项	状态
全量测试 (66 个)	66/66 passed
uvicorn server.main:app 启动	成功
/docs OpenAPI 文档	200 OK
GET /api/health	{"status": "ok"}
GET /api/projects	{"code": 0, "data": []}
POST /upload 格式校验	400 正确拦截
POST /upload 大小限制	413 正确拦截
启动方式

# 1. 启动 Redis
docker compose up -d redis

# 2. 启动 Celery worker
PYTHONPATH=src celery -A server.tasks.celery_app worker --loglevel=info

# 3. 启动 API
PYTHONPATH=src uvicorn server.main:app --reload --port 8000

# 4. 访问 OpenAPI 文档
open http://localhost:8000/docs

---
** Docker 配置 **
Dockerfile.backend — Python 3.11-slim，API 和 Worker 共用镜像，含 healthcheck
Dockerfile.frontend — 多阶段构建（node:20-alpine build → nginx:1.27-alpine serve），含 healthcheck
nginx.conf — / 静态文件、/api/ 反代、/ws/ WebSocket 代理（含 Upgrade header）
docker-compose.yml — 4 个服务（frontend/backend/worker/redis），Docker Volume 持久化
环境与安全
.env.example — 完整变量列表 + 中文注释，敏感信息不进 compose
server/config.py — 新增 WT_ALLOWED_ORIGINS 环境变量
server/main.py — CORS 从环境变量动态读取
开发体验
Makefile — dev / up / down / logs / test / migrate / build / clean 等命令
.dockerignore — 排除 git/cache/node_modules/runtime data
.gitignore — 完整规则，无多余文件进入版本控制
文档
README.md — 项目简介、Quick Start、本地开发、Docker 部署、配置说明、项目结构、API 文档链接
验收
66 tests pass
前端构建 ~137 KB gzipped（远低于 500 KB 限制）
git status 无 node_modules / __pycache__ / .env / *.db
部署流程：git clone → cp .env.example .env → 填 key → make up → 访问 http://localhost