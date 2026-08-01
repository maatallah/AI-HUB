"""Tests for the configuration system."""

from __future__ import annotations

from app.config import (
    DEFAULT_CONFIG,
    ConfigError,
    load_config,
    validate,
)

VALID_TOML = """
[database]
path = "database/ai_hub.db"

[monitoring]
enabled = true
interval_minutes = 30

[fallback]
max_chain_length = 3

[recommendation]
default_profile = "reasoning"

[dashboard]
refresh_seconds = 15

[logging]
level = "DEBUG"
"""


def test_defaults_used_when_file_missing(tmp_path):
    config = load_config(tmp_path / "does-not-exist.toml")
    assert config.database_path == DEFAULT_CONFIG["database"]["path"]
    assert config.monitoring_enabled is True
    assert config.monitoring_interval_minutes == 60
    assert config.fallback_max_chain_length == 5
    assert config.recommendation_default_profile == "coding"
    assert config.dashboard_refresh_seconds == 60
    assert config.logging_level == "INFO"


def test_file_overrides_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(VALID_TOML, encoding="utf-8")
    config = load_config(path)
    assert config.monitoring_interval_minutes == 30
    assert config.fallback_max_chain_length == 3
    assert config.recommendation_default_profile == "reasoning"
    assert config.dashboard_refresh_seconds == 15
    assert config.logging_level == "DEBUG"


def test_partial_file_keeps_other_defaults(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[logging]\nlevel = \"WARNING\"\n", encoding="utf-8")
    config = load_config(path)
    assert config.logging_level == "WARNING"
    assert config.monitoring_interval_minutes == 60
    assert config.database_path == "database/ai_hub.db"


def test_invalid_log_level_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[logging]\nlevel = \"LOUD\"\n", encoding="utf-8")
    try:
        load_config(path)
    except ConfigError as exc:
        assert "logging.level" in str(exc)
    else:
        raise AssertionError("Expected ConfigError for invalid log level.")


def test_invalid_interval_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[monitoring]\ninterval_minutes = 0\n", encoding="utf-8")
    try:
        load_config(path)
    except ConfigError as exc:
        assert "interval_minutes" in str(exc)
    else:
        raise AssertionError("Expected ConfigError for zero interval.")


def test_invalid_default_profile_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[recommendation]\ndefault_profile = \"not_a_profile\"\n", encoding="utf-8")
    try:
        load_config(path)
    except ConfigError as exc:
        assert "default_profile" in str(exc)
    else:
        raise AssertionError("Expected ConfigError for invalid profile.")


def test_secret_key_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[database]\napi_key = \"sk-123\"\n", encoding="utf-8")
    try:
        load_config(path)
    except ConfigError as exc:
        assert "api_key" in str(exc)
        assert "secret" in str(exc).lower()
    else:
        raise AssertionError("Expected ConfigError for secret-like key.")


def test_secret_key_rejected_nested(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("[monitoring]\n[monitoring.provider]\naccess_token = \"x\"\n", encoding="utf-8")
    try:
        load_config(path)
    except ConfigError:
        pass
    else:
        raise AssertionError("Expected ConfigError for nested secret-like key.")


def test_validate_returns_config():
    config = validate(
        {
            "database": {"path": "x.db"},
            "monitoring": {
                "enabled": True,
                "interval_minutes": 1,
                "timeout_seconds": 5,
                "failure_threshold": 2,
                "latency_threshold_ms": 5000,
            },
            "fallback": {"max_chain_length": 1},
            "recommendation": {"default_profile": "free"},
            "dashboard": {"refresh_seconds": 1},
            "logging": {"level": "CRITICAL"},
        }
    )
    assert config.recommendation_default_profile == "free"
    assert config.logging_level == "CRITICAL"
    assert config.monitoring_timeout_seconds == 5
    assert config.monitoring_failure_threshold == 2
    assert config.monitoring_latency_threshold_ms == 5000
