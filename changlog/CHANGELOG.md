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