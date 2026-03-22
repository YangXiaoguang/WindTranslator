# prompt
你是一名资深全栈工程师，现在需要将一个 Python CLI 工具（EPUB,PDF→中文PDF翻译器）重构为
带有高质量 Web 界面的全栈应用,同时保留原有命令行执行功能，在不影响web业务的情况下。在写任何代码之前，请先完成架构设计。

## 项目背景
现有 CLI 工具功能：
- 解析 EPUB&PDF 电子书，提取章节和段落
- 通过 LLM API批量翻译为中文
- 生成排版良好的中文 PDF
- 支持章节范围选择、配置文件、多 provider

## 架构要求

### 技术栈（硬性约束）
- 后端：Python 3.11+, FastAPI, SQLAlchemy (async), SQLite (开发) / PostgreSQL (生产)
- 前端：React 18+ with TypeScript, Vite, TailwindCSS, shadcn/ui
- 任务队列：Celery + Redis（翻译是长任务，必须异步）
- 实时通信：WebSocket（翻译进度推送）
- 容器化：Docker Compose 一键启动

### 设计原则
- 前后端完全分离，通过 REST API + WebSocket 通信
- 后端采用分层架构：Router → Service → Repository → Model
- 翻译引擎与 Web 层解耦，翻译核心逻辑可独立测试
- 所有 LLM provider 通过策略模式接入，新增 provider 只需加一个文件

## 交付物
请输出以下内容（不要写代码，只要设计）：

1. **完整的文件目录树**（精确到每个文件，附一句话说明）
2. **核心数据模型**（SQLAlchemy model 的字段定义，用伪代码）
3. **API 端点清单**（method, path, 功能, 请求/响应要点）
4. **WebSocket 事件协议**（事件名, payload 结构）
5. **Celery 任务流设计**（任务拆分粒度，失败重试策略）
6. **关键设计决策说明**（为什么选这个方案，tradeoff 是什么）

不要写实现代码，这一步只做设计。设计完成后等待我确认。

# WindTranslator 全栈架构设计
1. 完整文件目录树
```
WindTranslator/
├── src/
│   ├── epub_translator/              # 【保持不变】翻译引擎核心
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── cli.py                    # CLI 入口，不做任何修改
│   │   ├── config.py
│   │   ├── models.py                 # ContentBlock, Chapter
│   │   ├── pipeline.py              # TranslationPipeline（需加进度回调）
│   │   ├── parser/
│   │   ├── translator/
│   │   ├── renderer/
│   │   └── utils/
│   │
│   └── server/                       # 【新增】Web 后端
│       ├── __init__.py
│       ├── main.py                   # FastAPI app 工厂，挂载路由/中间件/CORS/WebSocket
│       ├── config.py                 # Pydantic Settings，读取环境变量（DB_URL, REDIS_URL, UPLOAD_DIR 等）
│       ├── database.py               # SQLAlchemy async engine + sessionmaker + Base
│       │
│       ├── models/                   # SQLAlchemy ORM 模型
│       │   ├── __init__.py
│       │   ├── book.py               # Book 表
│       │   ├── chapter.py            # Chapter 表
│       │   ├── translation_task.py   # TranslationTask 表
│       │   └── provider_config.py    # ProviderConfig 表（用户保存的 LLM 配置）
│       │
│       ├── schemas/                  # Pydantic request/response 模型
│       │   ├── __init__.py
│       │   ├── book.py               # BookCreate, BookResponse, BookDetail
│       │   ├── chapter.py            # ChapterResponse, ChapterPreview
│       │   ├── task.py               # TaskCreate, TaskResponse, TaskProgress
│       │   └── config.py             # ProviderConfigCreate, ProviderConfigResponse
│       │
│       ├── routers/                  # FastAPI 路由
│       │   ├── __init__.py
│       │   ├── books.py              # /api/books — 上传、列表、详情、删除
│       │   ├── tasks.py              # /api/tasks — 创建翻译任务、查询状态、取消
│       │   ├── configs.py            # /api/configs — LLM provider 配置 CRUD
│       │   └── downloads.py          # /api/downloads — 下载生成的 PDF
│       │
│       ├── services/                 # 业务逻辑层
│       │   ├── __init__.py
│       │   ├── book_service.py       # 上传解析、章节提取、元数据持久化
│       │   ├── task_service.py       # 创建任务、查询进度、取消任务
│       │   └── config_service.py     # provider 配置管理
│       │
│       ├── repositories/            # 数据访问层
│       │   ├── __init__.py
│       │   ├── book_repo.py
│       │   ├── task_repo.py
│       │   └── config_repo.py
│       │
│       ├── tasks/                    # Celery 任务
│       │   ├── __init__.py
│       │   ├── celery_app.py         # Celery 实例配置（broker=redis, backend=redis）
│       │   └── translate.py          # translate_book 任务：调用引擎 pipeline + 推送进度
│       │
│       └── ws/                       # WebSocket 管理
│           ├── __init__.py
│           └── manager.py            # ConnectionManager：房间管理、广播、断连清理
│
├── web/                              # 【新增】React 前端
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts                # dev proxy → localhost:8000
│   ├── tailwind.config.ts
│   ├── components.json               # shadcn/ui 配置
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── main.tsx                  # React 入口
│       ├── App.tsx                   # 路由配置
│       ├── api/
│       │   ├── client.ts             # axios 实例，baseURL + 拦截器
│       │   ├── books.ts              # book 相关 API 调用
│       │   ├── tasks.ts              # task 相关 API 调用
│       │   └── configs.ts            # config 相关 API 调用
│       ├── hooks/
│       │   ├── useWebSocket.ts       # WebSocket 连接管理 + 自动重连
│       │   └── useTaskProgress.ts    # 订阅特定任务进度
│       ├── pages/
│       │   ├── HomePage.tsx          # 上传区 + 最近任务列表
│       │   ├── BookDetailPage.tsx    # 章节预览 + 发起翻译
│       │   ├── TaskPage.tsx          # 翻译进度实时展示 + 下载
│       │   └── SettingsPage.tsx      # LLM provider 配置管理
│       ├── components/
│       │   ├── FileUploader.tsx      # 拖拽上传组件
│       │   ├── ChapterList.tsx       # 章节列表 + 范围选择
│       │   ├── ProgressCard.tsx      # 单任务进度卡片（进度条 + 日志）
│       │   ├── TaskTable.tsx         # 任务历史表格
│       │   ├── ProviderForm.tsx      # provider 配置表单
│       │   └── Layout.tsx            # 全局布局：侧边栏 + 主内容区
│       ├── lib/
│       │   └── utils.ts              # cn() 等工具函数（shadcn 标配）
│       └── types/
│           └── index.ts              # 前端 TypeScript 类型定义
│
├── alembic/                          # 【新增】数据库迁移
│   ├── alembic.ini
│   ├── env.py
│   └── versions/                     # 迁移脚本
│
├── docker/                           # 【新增】容器化配置
│   ├── Dockerfile.api                # Python 后端 + Celery worker
│   ├── Dockerfile.web                # Node 构建 → nginx 静态服务
│   └── nginx.conf                    # 反向代理：/api → api:8000, / → 前端静态
│
├── docker-compose.yml                # 一键启动：api, worker, web, redis, (pg)
├── .env.example                      # 环境变量模板
│
├── epub-translator                   # 【保持不变】CLI shell wrapper
├── pyproject.toml                    # 增加 server 依赖组
├── requirements.txt
├── conftest.py
└── tests/
    ├── conftest.py
    ├── test_pdf_parser.py            # 【保持不变】
    ├── test_pipeline.py              # 【保持不变】
    ├── test_routers/                 # 【新增】API 端点测试
    │   ├── test_books.py
    │   ├── test_tasks.py
    │   └── test_configs.py
    └── test_services/                # 【新增】服务层测试
        ├── test_book_service.py
        └── test_task_service.py
```

2. 核心数据模型

# server/models/book.py
```
class Book(Base):
    __tablename__ = "books"

    id: UUID                          # 主键
    filename: str                     # 原始文件名 "deep_learning.epub"
    file_path: str                    # 服务端存储路径（uploads/ 下）
    format: str                       # "epub" | "pdf"
    title: str                        # 解析得到的书名
    total_chapters: int               # 总章节数
    total_blocks: int                 # 总内容块数（用于进度计算）
    file_size: int                    # 字节数
    status: str                       # "parsed" | "error"
    created_at: datetime
    updated_at: datetime

    chapters: List[Chapter]           # 一对多
    tasks: List[TranslationTask]      # 一对多
```

# server/models/chapter.py
class Chapter(Base):
    __tablename__ = "chapters"

    id: UUID
    book_id: UUID                     # FK → books.id
    index: int                        # 章节序号（从 1 开始）
    title: str                        # 章节标题
    block_count: int                  # 该章节内容块数
    preview_text: str                 # 前 200 字，用于前端预览


# server/models/translation_task.py
class TranslationTask(Base):
    __tablename__ = "translation_tasks"

    id: UUID
    book_id: UUID                     # FK → books.id
    celery_task_id: str               # Celery AsyncResult ID
    status: str                       # "pending" | "running" | "completed" | "failed" | "cancelled"
    provider: str                     # "anthropic" | "openai" | "deepseek" | "custom"
    model: str                        # "claude-sonnet-4-6"
    chapter_range: Optional[str]      # "1-10" | None（全部）
    progress_current: int             # 已翻译块数
    progress_total: int               # 总块数
    output_path: Optional[str]        # 生成的 PDF 路径
    error_message: Optional[str]      # 失败原因
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


# server/models/provider_config.py
class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: UUID
    name: str                         # 用户自定义名称 "我的 Claude"
    provider: str                     # "anthropic" | "openai" | "deepseek" | "custom"
    model: str
    api_key_encrypted: str            # Fernet 加密存储
    base_url: Optional[str]           # 自定义端点
    is_default: bool                  # 是否为默认配置
    created_at: datetime
    updated_at: datetime
3. API 端点清单
Books
Method	Path	功能	要点
POST	/api/books/upload	上传电子书	multipart/form-data; 同步解析章节，返回 BookDetail
GET	/api/books	书籍列表	分页 ?page=1&size=20，返回 List[BookResponse]
GET	/api/books/{id}	书籍详情	含章节列表 List[ChapterPreview]
DELETE	/api/books/{id}	删除书籍	级联删除章节 + 关联任务 + 磁盘文件
Tasks
Method	Path	功能	要点
POST	/api/tasks	创建翻译任务	body: {book_id, config_id, chapter_range?}; 返回 TaskResponse + 202
GET	/api/tasks	任务列表	?status=running&book_id=xxx，分页
GET	/api/tasks/{id}	任务详情	含进度、错误信息
POST	/api/tasks/{id}/cancel	取消任务	调用 celery_app.control.revoke()
Downloads
Method	Path	功能	要点
GET	/api/downloads/{task_id}	下载 PDF	FileResponse, Content-Disposition
Configs
Method	Path	功能	要点
POST	/api/configs	新建 provider 配置	body: {name, provider, model, api_key, base_url?}
GET	/api/configs	配置列表	api_key 脱敏返回 sk-...****
PUT	/api/configs/{id}	更新配置	
DELETE	/api/configs/{id}	删除配置	检查是否有进行中任务引用
POST	/api/configs/{id}/test	测试连通性	发送一个短文本翻译，返回成功/失败
WebSocket
Path	功能
WS /ws/tasks/{task_id}	订阅单个任务的实时进度
4. WebSocket 事件协议
连接建立后，服务端单向推送（客户端只需监听）：


// 章节开始翻译
{
  "event": "chapter_start",
  "data": {
    "chapter_index": 3,
    "chapter_title": "Neural Networks",
    "total_chapters": 15
  }
}

// 翻译进度更新（每个 batch 完成后推送）
{
  "event": "progress",
  "data": {
    "chapter_index": 3,
    "blocks_done": 42,        // 全书累计已完成块数
    "blocks_total": 380,      // 全书总块数
    "percent": 11.05          // 百分比
  }
}

// 章节翻译完成
{
  "event": "chapter_done",
  "data": {
    "chapter_index": 3,
    "chapter_title": "Neural Networks"
  }
}

// 任务完成
{
  "event": "task_completed",
  "data": {
    "task_id": "uuid",
    "output_path": "/downloads/uuid",
    "elapsed_seconds": 342
  }
}

// 任务失败
{
  "event": "task_failed",
  "data": {
    "task_id": "uuid",
    "error": "API 返回空内容列表",
    "failed_at_chapter": 7
  }
}

// 心跳（每 30s，防止连接被中间件/代理断开）
{
  "event": "heartbeat",
  "data": { "ts": 1711036800 }
}
5. Celery 任务流设计
任务拆分粒度
一个翻译任务 = 一个 Celery Task，粒度为「整本书（或指定章节范围）」。不按章节拆分为独立 Celery 任务，原因：

章节间共享同一个 LLM provider 连接和缓存实例，拆分会造成大量连接创建/销毁
当前 LLMTranslator 的 batch 机制本身已做了段落级并发优化
进度报告通过回调函数实现，不依赖 Celery 的 task 粒度
任务执行流程

translate_book(task_id, book_id, config_id, chapter_range)
│
├── 1. 从 DB 读取 ProviderConfig → 构建 TranslatorConfig
├── 2. 从磁盘读取源文件 → get_parser() → get_chapters()
├── 3. 应用 chapter_range 过滤
├── 4. 构建 LLMTranslator
├── 5. 逐章翻译，每完成一个 block batch：
│      ├── 更新 DB: task.progress_current += batch_size
│      └── 通过 Redis Pub/Sub → WebSocket 推送 progress 事件
├── 6. 调用 PDFRenderer 生成 PDF
├── 7. 更新 DB: task.status = "completed", task.output_path = ...
└── 8. 推送 task_completed 事件
进度回调机制
在 TranslationPipeline 中新增一个可选的 on_progress 回调参数：


# pipeline.py 的改动（唯一需要修改引擎的地方）
def run(self, ..., on_progress: Callable[[int, int, str], None] | None = None):
    # on_progress(blocks_done, blocks_total, chapter_title)
CLI 调用时不传回调（行为不变），Celery 任务传入回调用于推送。

失败重试策略

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,          # 30 秒后重试
    autoretry_for=(ConnectionError, TimeoutError),  # 仅网络类错误自动重试
    retry_backoff=True,              # 指数退避
)
def translate_book(self, task_id, ...):
    try:
        ...
    except (AuthenticationError, ValueError) as e:
        # 不可重试错误 → 直接标记失败
        mark_failed(task_id, str(e))
        raise  # 不 retry
可重试：网络超时、连接断开、API 限流 (429) → 自动重试最多 2 次，指数退避
不可重试：认证失败、模型不存在、文件解析错误 → 直接标记 failed，不重试
取消：前端调用 cancel API → revoke(task_id, terminate=True) + 在翻译循环中检查 self.is_aborted()
WebSocket 推送实现
Celery worker 通过 Redis Pub/Sub 发布进度消息（channel = task:{task_id}），FastAPI 的 WebSocket endpoint 订阅对应 channel 并转发给前端。这样 worker 和 API server 进程解耦，无需共享内存。

6. 关键设计决策说明
决策 1：翻译引擎只加回调，不改架构
方案：pipeline.py 唯一改动是 run() 新增可选 on_progress 回调参数。

Why：引擎经过完整的重构和测试（42 个用例），是成熟稳定的核心。Web 层应该"包装"引擎，而不是侵入它。CLI 调用不传回调，行为完全不变。

Tradeoff：回调只能在 block batch 粒度报告进度（非实时逐字），但这足够了——翻译一个 batch 通常 2-5 秒，用户体验完全可接受。

决策 2：一个 Celery Task = 一整本书，而非按章节拆
方案：一个翻译请求 = 一个 Celery Task。

Why：

LLMTranslator 内部维护连接、缓存实例，频繁创建销毁浪费资源
按章节拆分还需要一个 chord/chain 来聚合结果和生成 PDF，增加复杂度
当前引擎的 batch 机制已经在段落级做了优化
Tradeoff：单任务失败后只能从头重试整本书。但 SQLite 翻译缓存会命中已翻译的段落，实际重试时只需翻译失败点之后的内容，开销很小。

决策 3：Redis Pub/Sub 做进度推送，而非 Celery state
方案：Worker 发布到 Redis channel task:{id}，FastAPI WebSocket handler 订阅并转发。

Why：

Celery 的 update_state() 需要轮询，延迟高（秒级）
Redis Pub/Sub 是推送模式，延迟在毫秒级
WebSocket handler 直接订阅 Redis，不需要引入额外组件
Tradeoff：如果 WebSocket 断开期间有消息发出，这些消息会丢失。解决方式：前端重连后调用 GET /api/tasks/{id} 获取 DB 中最新进度（数据库是持久化的 source of truth）。

决策 4：API Key 加密存储
方案：使用 cryptography.Fernet 对称加密，密钥从环境变量 ENCRYPTION_KEY 读取。

Why：用户的 LLM API Key 是敏感信息，明文存 DB 不可接受。

Tradeoff：Fernet 是对称加密，拿到 key 就能解密。生产环境应使用 Vault 等密钥管理服务，但对于单机/小团队部署，环境变量级别的保护是合理的起点。

决策 5：前后端完全分离 + nginx 反代
方案：Vite 构建静态文件 → nginx 服务；API 请求 /api/* 和 /ws/* 反代到 FastAPI。

Why：

开发时前后端可独立启动（Vite dev server + uvicorn），互不阻塞
生产部署时前端是纯静态文件，CDN 友好
FastAPI 不需要处理静态文件，职责单一
Tradeoff：多一个 nginx 容器。但 nginx 配置简单，资源占用极小（<10MB），换来的部署灵活性值得。

决策 6：SQLite (开发) / PostgreSQL (生产) 切换
方案：通过 DATABASE_URL 环境变量切换，SQLAlchemy async 同时支持 aiosqlite 和 asyncpg。Alembic 管理迁移。

Why：SQLite 零配置，开发体验好；PostgreSQL 支持并发写入，生产必需。

Tradeoff：需要确保 SQL 兼容两种方言（避免 PG-only 语法）。实际上本项目的查询都很简单，不会遇到兼容性问题。

Docker Compose 服务编排

┌─────────┐     ┌───────────┐     ┌─────────────┐
│  nginx  │────▶│  api      │────▶│  redis      │
│  :80    │     │  :8000    │     │  :6379      │
│         │     │  FastAPI  │     │             │
└─────────┘     └───────────┘     └──────┬──────┘
                                         │
                ┌───────────┐            │
                │  worker   │────────────┘
                │  Celery   │
                └───────────┘
api：uvicorn server.main:app，含 WebSocket endpoint
worker：celery -A server.tasks.celery_app worker，同一镜像不同启动命令
redis：broker + pub/sub + result backend
nginx：静态文件 + 反向代理
开发环境省略 nginx，Vite 直连 API
以上是完整设计，等你确认后开始实现。如有任何部分需要调整，请指出。