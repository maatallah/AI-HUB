"""AI-Hub Phase 1 initial provider seed dataset.

Populates the manual provider registry with well-known AI providers.

Safety rules:
  * metadata only - no API keys, no secrets, no credentials
  * idempotent - providers that already exist are skipped, never modified
  * non-destructive - no provider is ever deleted or changed here
  * unknown values stay NULL (Constitution Article 10)

Run from the repository root:

    python scripts/seed_providers.py

Field names follow the providers table (v1.1 Section 8).
A base_url or documentation_url left as None means the value is not yet
confirmed and must be validated during Phase 2 (never fabricated).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain script from anywhere under the repository.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config  # noqa: E402
from core import providers  # noqa: E402
from database import database as db_util  # noqa: E402

#: Representative providers. Metadata only.
PROVIDERS = [
    {
        "name": "OpenAI",
        "company": "OpenAI",
        "api_type": "Native",
        "base_url": "https://api.openai.com/v1",
        "documentation_url": "https://platform.openai.com/docs",
    },
    {
        "name": "Google Gemini",
        "company": "Google",
        "api_type": "Native",
        "base_url": "https://generativelanguage.googleapis.com",
        "documentation_url": "https://ai.google.dev",
    },
    {
        "name": "Anthropic",
        "company": "Anthropic",
        "api_type": "Native",
        "base_url": "https://api.anthropic.com",
        "documentation_url": "https://docs.anthropic.com",
    },
    {
        "name": "OpenRouter",
        "company": "OpenRouter",
        "api_type": "OpenAI Compatible",
        "base_url": "https://openrouter.ai/api/v1",
        "documentation_url": "https://openrouter.ai/docs",
    },
    {
        "name": "Blackbox AI",
        "company": "Blackbox AI",
        "api_type": None,
        "base_url": None,
        "documentation_url": "https://docs.blackbox.ai",
    },
    {
        "name": "DeepSeek",
        "company": "DeepSeek",
        "api_type": "OpenAI Compatible",
        "base_url": "https://api.deepseek.com",
        "documentation_url": "https://api-docs.deepseek.com",
    },
    {
        "name": "MiniMax",
        "company": "MiniMax",
        "api_type": "OpenAI Compatible",
        "base_url": None,
        "documentation_url": "https://platform.minimaxi.com",
    },
    {
        "name": "Qwen",
        "company": "Alibaba",
        "api_type": "OpenAI Compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "documentation_url": "https://help.aliyun.com/zh/modelstudio",
    },
    {
        "name": "GitHub Models",
        "company": "GitHub",
        "api_type": "OpenAI Compatible",
        "base_url": "https://models.github.ai/inference",
        "documentation_url": "https://github.com/marketplace/models",
    },
]


def _provider_names(conn):
    return {row["name"] for row in providers.list_providers(conn)}


def main() -> None:
    config = load_config()
    conn = db_util.initialize(config.database_path)
    db_util.validate_schema(conn)
    try:
        existing = _provider_names(conn)
        added: list[str] = []
        skipped: list[str] = []

        for data in PROVIDERS:
            if data["name"] in existing:
                skipped.append(data["name"])
                continue
            providers.add_provider(
                conn,
                name=data["name"],
                company=data["company"],
                api_type=data["api_type"],
                base_url=data["base_url"],
                documentation_url=data["documentation_url"],
                status="NEW",
            )
            added.append(data["name"])

        print(f"Providers added: {len(added)}")
        for name in added:
            print(f"  + {name}")
        if skipped:
            print(f"Providers skipped (already present): {len(skipped)}")
            for name in skipped:
                print(f"  = {name}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
