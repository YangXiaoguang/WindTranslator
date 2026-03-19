import os
import pytest
from pathlib import Path
from epub_translator.config import load_config, DEFAULT_PROVIDER, DEFAULT_MODEL


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    cfg = load_config()
    assert cfg.provider == DEFAULT_PROVIDER
    assert cfg.model == DEFAULT_MODEL
    assert cfg.api_key == "env-key"


def test_yaml_overrides_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "translator.yaml").write_text(
        "provider: openai\nmodel: gpt-4o\napi_key: yaml-key\n"
    )
    cfg = load_config()
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-4o"
    assert cfg.api_key == "yaml-key"


def test_explicit_config_path(tmp_path):
    cfg_file = tmp_path / "my_config.yaml"
    cfg_file.write_text("provider: deepseek\nmodel: deepseek-chat\napi_key: ds-key\n")
    cfg = load_config(str(cfg_file))
    assert cfg.provider == "deepseek"
    assert cfg.api_key == "ds-key"


def test_placeholder_api_key_uses_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "translator.yaml").write_text("api_key: YOUR_API_KEY_HERE\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-env-key")
    cfg = load_config()
    assert cfg.api_key == "real-env-key"


def test_cache_db_custom_path(tmp_path):
    cfg_file = tmp_path / "translator.yaml"
    cfg_file.write_text(f"api_key: k\ncache_db: {tmp_path}/my.db\n")
    cfg = load_config(str(cfg_file))
    assert cfg.cache_db == tmp_path / "my.db"


def test_system_prompt_auto_discovered(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "system_prompt.md").write_text("Custom prompt")
    cfg = load_config()
    assert cfg.system_prompt_path == tmp_path / "system_prompt.md"
