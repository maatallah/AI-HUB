"""AI-Hub configuration system.

Phase 1 scope:
  * local configuration only (TOML, Python 3.11+ stdlib ``tomllib``)
  * documented defaults (see ``DEFAULT_CONFIG`` and ``config.toml``)
  * validation of every known value
  * rejection of any configuration key that looks like a secret

Safety: AI-Hub never stores raw secrets. Any key whose name suggests a
credential (key, token, secret, password, credential, apikey) is rejected.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

#: Default configuration file relative to the repository root.
CONFIG_FILENAME = "config.toml"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Recommendation profiles defined by v1.2 Section 2.
VALID_PROFILES = {"coding", "reasoning", "free", "long_context"}

#: Logging levels accepted by the configuration.
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

#: Substrings that mark a configuration key as a potential secret.
SECRET_KEYWORDS = ("key", "token", "secret", "password", "credential", "apikey")


class ConfigError(ValueError):
    """Raised when configuration is invalid or rejected for safety reasons."""


#: Documented defaults (v1.2 Section 10).
DEFAULT_CONFIG: dict = {
    "database": {
        "path": "database/ai_hub.db",
    },
    "monitoring": {
        "enabled": True,
        "interval_minutes": 60,
    },
    "fallback": {
        "max_chain_length": 5,
    },
    "recommendation": {
        "default_profile": "coding",
    },
    "dashboard": {
        "refresh_seconds": 60,
    },
    "logging": {
        "level": "INFO",
    },
}


@dataclass(frozen=True)
class Config:
    """Validated effective configuration."""

    database_path: str
    monitoring_enabled: bool
    monitoring_interval_minutes: int
    fallback_max_chain_length: int
    recommendation_default_profile: str
    dashboard_refresh_seconds: int
    logging_level: str


def _reject_secrets(data: dict, section: str = "") -> None:
    """Walk every key and reject anything that resembles a credential."""
    for key, value in data.items():
        location = f"{section}.{key}" if section else key
        lowered = key.lower()
        if any(word in lowered for word in SECRET_KEYWORDS):
            raise ConfigError(
                f"Configuration key '{location}' looks like a secret and is "
                "not permitted. AI-Hub never stores raw credentials "
                "(Constitution Article 6)."
            )
        if isinstance(value, dict):
            _reject_secrets(value, location)


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay into a deep copy of base."""
    result = {k: dict(v) if isinstance(v, dict) else v for k, v in base.items()}
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _require(d: dict, section: str, key: str) -> object:
    if section not in d or not isinstance(d[section], dict):
        raise ConfigError(f"Missing configuration section [{section}].")
    if key not in d[section]:
        raise ConfigError(f"Missing configuration value '{section}.{key}'.")
    return d[section][key]


def validate(data: dict) -> Config:
    """Validate a merged configuration dictionary and return a Config object."""
    _reject_secrets(data)

    db_path = _require(data, "database", "path")
    if not isinstance(db_path, str) or not db_path.strip():
        raise ConfigError("database.path must be a non-empty string.")

    monitoring = data["monitoring"]
    if not isinstance(monitoring.get("enabled"), bool):
        raise ConfigError("monitoring.enabled must be a boolean.")
    if not isinstance(monitoring.get("interval_minutes"), int) or monitoring["interval_minutes"] <= 0:
        raise ConfigError("monitoring.interval_minutes must be a positive integer.")

    fallback = data["fallback"]
    if not isinstance(fallback.get("max_chain_length"), int) or fallback["max_chain_length"] < 1:
        raise ConfigError("fallback.max_chain_length must be an integer >= 1.")

    recommendation = data["recommendation"]
    profile = recommendation.get("default_profile")
    if profile not in VALID_PROFILES:
        raise ConfigError(
            f"recommendation.default_profile must be one of {sorted(VALID_PROFILES)}; got {profile!r}."
        )

    dashboard = data["dashboard"]
    if not isinstance(dashboard.get("refresh_seconds"), int) or dashboard["refresh_seconds"] <= 0:
        raise ConfigError("dashboard.refresh_seconds must be a positive integer.")

    logging_ = data["logging"]
    level = logging_.get("level")
    if level not in VALID_LOG_LEVELS:
        raise ConfigError(
            f"logging.level must be one of {sorted(VALID_LOG_LEVELS)}; got {level!r}."
        )

    return Config(
        database_path=db_path.strip(),
        monitoring_enabled=monitoring["enabled"],
        monitoring_interval_minutes=monitoring["interval_minutes"],
        fallback_max_chain_length=fallback["max_chain_length"],
        recommendation_default_profile=profile,
        dashboard_refresh_seconds=dashboard["refresh_seconds"],
        logging_level=level,
    )


def load_config(path=None):
    """Load and validate configuration.

    * ``path`` is None: use the repository ``config.toml`` if it exists,
      otherwise fall back to defaults.
    * ``path`` is a file: load, merge over defaults, validate.

    Returns a :class:`Config`.
    """
    if path is None:
        path = PROJECT_ROOT / CONFIG_FILENAME

    cfg_path = Path(path)
    overlay: dict = {}
    if cfg_path.is_file():
        with open(cfg_path, "rb") as handle:
            overlay = tomllib.load(handle)

    merged = _deep_merge(DEFAULT_CONFIG, overlay)
    return validate(merged)


def effective_config_text(config: Config) -> str:
    """Render the effective configuration as human-readable TOML."""
    return (
        "[database]\n"
        f'path = "{config.database_path}"\n'
        "\n[monitoring]\n"
        f"enabled = {str(config.monitoring_enabled).lower()}\n"
        f"interval_minutes = {config.monitoring_interval_minutes}\n"
        "\n[fallback]\n"
        f"max_chain_length = {config.fallback_max_chain_length}\n"
        "\n[recommendation]\n"
        f'default_profile = "{config.recommendation_default_profile}"\n'
        "\n[dashboard]\n"
        f"refresh_seconds = {config.dashboard_refresh_seconds}\n"
        "\n[logging]\n"
        f'level = "{config.logging_level}"\n'
    )
