"""Tests for the VS Code routing decision feature registration (post-v1 M2).

The VS Code extension is authored in TypeScript; its unit tests run via npm
(``connectors/vscode``). This Python test independently verifies the M2 R5
contract directly against the committed ``src/features.ts`` source, so the
requirement is validated within the Python test suite as the M2 scope mandates
(scope Section 8: ``tests/test_vscode_route_feature.py``).
"""

from __future__ import annotations

from pathlib import Path

_FEATURES_SRC = (
    Path(__file__).resolve().parents[1]
    / "connectors"
    / "vscode"
    / "src"
    / "features.ts"
)


def _source() -> str:
    assert _FEATURES_SRC.exists(), f"missing {_FEATURES_SRC}"
    return _FEATURES_SRC.read_text(encoding="utf-8")


def test_route_decide_feature_declared():
    src = _source()
    assert 'commandId: "ai-hub.routeDecide"' in src
    assert 'title: "Route Decision"' in src
    assert 'requiresInput: "task"' in src


def test_route_decide_builds_exact_cli_arguments():
    src = _source()
    assert (
        'buildArgs: (task) => ["route", "decide", "--task", task, "--json"]'
    ) in src


def test_route_decide_uses_read_only_cli_subcommand():
    src = _source()
    assert '"route", "decide"' in src
    assert "record" not in src.split('commandId: "ai-hub.routeDecide"')[
        1
    ].split("commandId:")[0]
