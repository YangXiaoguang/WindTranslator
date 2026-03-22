# WindTranslator

将英文 EPUB / PDF 电子书翻译为中文 PDF 的全栈翻译工具。

基于大语言模型（Claude、GPT、DeepSeek 等）进行高质量翻译，保留原书结构，支持实时进度追踪。

<!-- TODO: 功能截图 -->

## Quick Start

三步启动：

```bash
# 1. 克隆项目
git clone https://github.com/YangXiaoguang/WindTranslator.git
cd WindTranslator

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，生成并填入 WT_ENCRYPTION_KEY:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 3. 启动
make up
```

打开浏览器访问 **http://localhost**，上传书籍即可开始翻译。

## 功能特性

- **多格式支持** — EPUB、PDF 输入，PDF 输出
- **多 LLM 供应商** — Anthropic Claude、OpenAI GPT、DeepSeek、自定义 OpenAI 兼容接口
- **实时翻译进度** — WebSocket 推送，双栏原文/译文对照预览
- **章节选择** — 可选择翻译全书或指定章节
- **断点续译** — 翻译中断后跳过已完成段落，继续翻译
- **批量翻译** — 智能分批，平衡速度与质量
- **容器化部署** — Docker Compose 一键启动

## 本地开发

### 前置依赖

- Python 3.9+
- Node.js 18+
- Redis（或通过 `make dev-redis` 用 Docker 启动）

### 安装

```bash
# Python 依赖
pip install -e ".[dev]"

# 前端依赖
cd web && npm install && cd ..

# 数据库迁移
make migrate

# 启动开发服务器（前后端热重载）
make dev
```

- 前端: http://localhost:5173
- 后端: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 运行测试

```bash
make test
```

## Docker 部署

```bash
# 构建并启动
make up

# 查看日志
make logs

# 停止
make down
```

数据通过 Docker Volume 持久化，`docker compose down` 后重启不丢失数据。
如需完全清理（含数据）：`make clean-docker`

## CLI 命令行工具

也可以直接通过命令行使用翻译功能（无需启动 Web 服务）：

```bash
# 预览章节列表
epub-translator your_book.epub --list

# 翻译全书
epub-translator your_book.epub

# 只翻译第 1-5 章
epub-translator your_book.epub --chapters 1-5

# 指定输出路径
epub-translator your_book.epub -o ~/Desktop/output_zh.pdf
```

## 配置说明

所有配置通过环境变量注入，前缀 `WT_`：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WT_DATABASE_URL` | 数据库连接（SQLite / PostgreSQL） | `sqlite+aiosqlite:///./data/wind_translator.db` |
| `WT_REDIS_URL` | Redis 连接 | `redis://localhost:6379/0` |
| `WT_ENCRYPTION_KEY` | Fernet 加密密钥 | （必填） |
| `WT_UPLOAD_DIR` | 上传文件目录 | `uploads` |
| `WT_OUTPUT_DIR` | 输出文件目录 | `outputs` |
| `WT_BATCH_CHAR_LIMIT` | 批量翻译字符上限 | `2000` |
| `WT_MAX_RETRIES` | 翻译重试次数 | `3` |
| `WT_ALLOWED_ORIGINS` | CORS 允许来源 | `http://localhost,...` |
| `WT_PORT` | 前端对外端口 | `80` |

### 支持的 LLM 供应商

| Provider | 说明 |
|----------|------|
| `anthropic` | Anthropic Claude（claude-sonnet-4-6 等） |
| `openai` | OpenAI GPT（gpt-4o 等） |
| `deepseek` | DeepSeek（deepseek-chat 等） |
| `custom` | 自定义 OpenAI 兼容 API（需提供 Base URL） |

## 项目结构

```
WindTranslator/
├── src/
│   ├── epub_translator/     # 翻译引擎核心（解析、翻译、渲染）
│   └── server/              # FastAPI 后端
│       ├── models/          # SQLAlchemy 数据模型
│       ├── routers/         # REST API 路由
│       ├── repositories/    # 数据访问层
│       ├── schemas/         # Pydantic 请求/响应模型
│       ├── tasks/           # Celery 异步任务
│       ├── translator/      # LLM 翻译引擎
│       ├── ws/              # WebSocket 实时推送
│       └── main.py          # FastAPI 入口
├── web/                     # React 前端
│   └── src/
│       ├── pages/           # 页面组件
│       ├── components/      # UI + 领域组件
│       ├── api/             # API 客户端
│       ├── stores/          # Zustand 状态
│       └── hooks/           # 自定义 Hook
├── docker/                  # Docker 配置
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
├── alembic/                 # 数据库迁移
├── tests/                   # 测试
├── docker-compose.yml
├── Makefile
└── .env.example
```

## API 文档

启动后端后访问自动生成的交互式文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
