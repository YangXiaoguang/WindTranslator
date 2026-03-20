import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

# ── Translation tuning ─────────────────────────────────────────────────────────
BATCH_CHAR_LIMIT = 2000   # soft cap for batching paragraphs into one API call
MAX_RETRIES = 3
SEPARATOR = "\n<<<SPLIT>>>\n"

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-sonnet-4-6"

# ── Search paths ───────────────────────────────────────────────────────────────
# Intentionally functions, not module-level constants: Path.cwd() must be
# evaluated at call time, not at import time, so callers that change directory
# after import still get the correct working-directory path.

def _config_search_paths() -> list:
    return [Path.cwd() / "translator.yaml", Path.home() / ".translator.yaml"]


def _system_prompt_search_paths() -> list:
    return [Path.cwd() / "system_prompt.md", Path.home() / ".system_prompt.md"]


@dataclass
class TranslatorConfig:
    provider: str = DEFAULT_PROVIDER       # anthropic | openai | deepseek | custom
    api_key: Optional[str] = None
    model: str = DEFAULT_MODEL
    base_url: Optional[str] = None         # for openai-compatible endpoints
    system_prompt_path: Optional[Path] = None
    cache_enabled: bool = True
    cache_db: Path = field(
        default_factory=lambda: Path.home() / ".epub_translator" / "cache.db"
    )


def load_config(config_path: Optional[str] = None) -> TranslatorConfig:
    """Load config from YAML, falling back to env vars for missing fields."""
    paths = ([Path(config_path)] if config_path else []) + _config_search_paths()

    data: dict = {}
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            log.info("使用配置文件：%s", p)
            break
    else:
        log.info("未找到 translator.yaml，使用环境变量 / 命令行参数")

    cfg = TranslatorConfig(
        provider=data.get("provider", DEFAULT_PROVIDER),
        model=data.get("model", DEFAULT_MODEL),
        base_url=data.get("base_url"),
        cache_enabled=data.get("cache_enabled", True),
    )

    if "cache_db" in data:
        cfg.cache_db = Path(data["cache_db"]).expanduser()

    # system_prompt_path: config file > auto-search
    if "system_prompt_path" in data:
        cfg.system_prompt_path = Path(data["system_prompt_path"]).expanduser()
    else:
        for sp in _system_prompt_search_paths():
            if sp.exists():
                cfg.system_prompt_path = sp
                break

    # api_key: config file > provider env var > generic API_KEY env var
    raw_key = data.get("api_key", "")
    if raw_key and raw_key != "YOUR_API_KEY_HERE":
        cfg.api_key = raw_key
    else:
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        env_var = env_map.get(cfg.provider, "API_KEY")
        cfg.api_key = os.environ.get(env_var) or os.environ.get("API_KEY")

    return cfg
