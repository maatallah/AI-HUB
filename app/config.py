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

import json
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
        "timeout_seconds": 10,
        "failure_threshold": 3,
        "latency_threshold_ms": 10000,
    },
    "scoring": {
        "aging_fresh_days": 30,
        "aging_aging_days": 90,
        "aging_old_days": 180,
        "derive_operational": True,
    },
    "fallback": {
        "max_chain_length": 5,
    },
    "recommendation": {
        "default_profile": "coding",
        "decision_version": "3.0.0",
    },
    "dashboard": {
        "refresh_seconds": 60,
    },
    "discovery": {
        "enabled": False,
        "allowlisted_urls": [],
        "timeout_seconds": 10,
        "import_dir": "data/discovery",
    },
    "benchmark": {
        "import_dir": "data/benchmarks",
    },
    "trend": {
        "window_days": 90,
        "min_points": 3,
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
    monitoring_timeout_seconds: int
    monitoring_failure_threshold: int
    monitoring_latency_threshold_ms: int
    scoring_aging_fresh_days: int
    scoring_aging_aging_days: int
    scoring_aging_old_days: int
    scoring_derive_operational: bool
    fallback_max_chain_length: int
    recommendation_default_profile: str
    recommendation_decision_version: str
    dashboard_refresh_seconds: int
    discovery_enabled: bool
    discovery_allowlisted_urls: list
    discovery_timeout_seconds: int
    discovery_import_dir: str
    benchmark_import_dir: str
    trend_window_days: int
    trend_min_points: int
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


def _validate_url_safety(url: str) -> None:
    """Accept only http(s) URLs without credentials or secret-like query keys."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ConfigError(
            f"discovery.allowlisted_urls entry {url!r} must be an http(s) URL."
        )
    if not parsed.hostname:
        raise ConfigError(f"discovery.allowlisted_urls entry {url!r} has no host.")
    if parsed.username is not None or parsed.password is not None:
        raise ConfigError(
            f"discovery.allowlisted_urls entry {url!r} embeds credentials; "
            "URLs must never contain credentials (Constitution Article 6)."
        )
    for key in parse_qs(parsed.query):
        if any(word in key.lower() for word in SECRET_KEYWORDS):
            raise ConfigError(
                f"discovery.allowlisted_urls entry {url!r} carries a "
                "secret-like query key."
            )


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
    if not isinstance(monitoring.get("timeout_seconds"), int) or monitoring["timeout_seconds"] <= 0:
        raise ConfigError("monitoring.timeout_seconds must be a positive integer.")
    if (
        not isinstance(monitoring.get("failure_threshold"), int)
        or monitoring["failure_threshold"] < 1
    ):
        raise ConfigError("monitoring.failure_threshold must be an integer >= 1.")
    if (
        not isinstance(monitoring.get("latency_threshold_ms"), int)
        or monitoring["latency_threshold_ms"] <= 0
    ):
        raise ConfigError("monitoring.latency_threshold_ms must be a positive integer.")

    scoring = data["scoring"]
    for key in ("aging_fresh_days", "aging_aging_days", "aging_old_days"):
        if not isinstance(scoring.get(key), int) or scoring[key] <= 0:
            raise ConfigError(f"scoring.{key} must be a positive integer.")
    if not (
        scoring["aging_fresh_days"] < scoring["aging_aging_days"] < scoring["aging_old_days"]
    ):
        raise ConfigError(
            "scoring aging boundaries must be strictly increasing:"
            " fresh < aging < old."
        )
    if not isinstance(scoring.get("derive_operational"), bool):
        raise ConfigError("scoring.derive_operational must be a boolean.")

    fallback = data["fallback"]
    if not isinstance(fallback.get("max_chain_length"), int) or fallback["max_chain_length"] < 1:
        raise ConfigError("fallback.max_chain_length must be an integer >= 1.")

    recommendation = data["recommendation"]
    profile = recommendation.get("default_profile")
    if profile not in VALID_PROFILES:
        raise ConfigError(
            f"recommendation.default_profile must be one of {sorted(VALID_PROFILES)}; got {profile!r}."
        )
    decision_version = recommendation.get("decision_version")
    if not isinstance(decision_version, str) or not decision_version.strip():
        raise ConfigError("recommendation.decision_version must be a non-empty string.")

    dashboard = data["dashboard"]
    if not isinstance(dashboard.get("refresh_seconds"), int) or dashboard["refresh_seconds"] <= 0:
        raise ConfigError("dashboard.refresh_seconds must be a positive integer.")

    discovery_ = data["discovery"]
    if not isinstance(discovery_.get("enabled"), bool):
        raise ConfigError("discovery.enabled must be a boolean.")
    urls = discovery_.get("allowlisted_urls")
    if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
        raise ConfigError("discovery.allowlisted_urls must be a list of URL strings.")
    for url in urls:
        _validate_url_safety(url)
    if (
        not isinstance(discovery_.get("timeout_seconds"), int)
        or discovery_["timeout_seconds"] <= 0
    ):
        raise ConfigError("discovery.timeout_seconds must be a positive integer.")
    if not isinstance(discovery_.get("import_dir"), str) or not discovery_["import_dir"].strip():
        raise ConfigError("discovery.import_dir must be a non-empty string.")

    benchmark_ = data["benchmark"]
    if not isinstance(benchmark_.get("import_dir"), str) or not benchmark_["import_dir"].strip():
        raise ConfigError("benchmark.import_dir must be a non-empty string.")

    trend = data["trend"]
    if not isinstance(trend.get("window_days"), int) or trend["window_days"] <= 0:
        raise ConfigError("trend.window_days must be a positive integer.")
    if not isinstance(trend.get("min_points"), int) or trend["min_points"] < 1:
        raise ConfigError("trend.min_points must be an integer >= 1.")

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
        monitoring_timeout_seconds=monitoring["timeout_seconds"],
        monitoring_failure_threshold=monitoring["failure_threshold"],
        monitoring_latency_threshold_ms=monitoring["latency_threshold_ms"],
        scoring_aging_fresh_days=scoring["aging_fresh_days"],
        scoring_aging_aging_days=scoring["aging_aging_days"],
        scoring_aging_old_days=scoring["aging_old_days"],
        scoring_derive_operational=scoring["derive_operational"],
        fallback_max_chain_length=fallback["max_chain_length"],
        recommendation_default_profile=profile,
        recommendation_decision_version=decision_version,
        dashboard_refresh_seconds=dashboard["refresh_seconds"],
        discovery_enabled=discovery_["enabled"],
        discovery_allowlisted_urls=urls,
        discovery_timeout_seconds=discovery_["timeout_seconds"],
        discovery_import_dir=discovery_["import_dir"],
        benchmark_import_dir=benchmark_["import_dir"].strip(),
        trend_window_days=trend["window_days"],
        trend_min_points=trend["min_points"],
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
        f"timeout_seconds = {config.monitoring_timeout_seconds}\n"
        f"failure_threshold = {config.monitoring_failure_threshold}\n"
        f"latency_threshold_ms = {config.monitoring_latency_threshold_ms}\n"
        "\n[scoring]\n"
        f"aging_fresh_days = {config.scoring_aging_fresh_days}\n"
        f"aging_aging_days = {config.scoring_aging_aging_days}\n"
        f"aging_old_days = {config.scoring_aging_old_days}\n"
        f"derive_operational = {str(config.scoring_derive_operational).lower()}\n"
        "\n[fallback]\n"
        f"max_chain_length = {config.fallback_max_chain_length}\n"
        "\n[recommendation]\n"
        f'default_profile = "{config.recommendation_default_profile}"\n'
        f'decision_version = "{config.recommendation_decision_version}"\n'
        "\n[dashboard]\n"
        f"refresh_seconds = {config.dashboard_refresh_seconds}\n"
        "\n[discovery]\n"
        f"enabled = {str(config.discovery_enabled).lower()}\n"
        "allowlisted_urls = "
        + (
            f"[{', '.join(json.dumps(u) for u in config.discovery_allowlisted_urls)}]\n"
            if config.discovery_allowlisted_urls
            else "[]\n"
        )
        + f"timeout_seconds = {config.discovery_timeout_seconds}\n"
        + f'import_dir = "{config.discovery_import_dir}"\n'
        + "\n[benchmark]\n"
        + f'import_dir = "{config.benchmark_import_dir}"\n'
        + "\n[trend]\n"
        + f"window_days = {config.trend_window_days}\n"
        + f"min_points = {config.trend_min_points}\n"
        + "\n[logging]\n"
        + f'level = "{config.logging_level}"\n'
    )
