"""Recommendation explanation generation (Phase 3).

Produces the human-readable explanation (Constitution Article 4: what / why /
evidence / confidence) and the structured score breakdown recorded in the
``recommendations`` table (v1.2 Section 8).
"""

from __future__ import annotations


def build_explanation(task, profile, row, final, breakdown, weights, flags) -> str:
    """Return a human-readable explanation for a recommendation."""
    lines = [
        f"Recommendation for task {task!r} using profile {profile!r}.",
        f"Provider {row['provider_name']} model {row['model_identifier']}."
        f" Final score {final:.2f}.",
        "Dimension breakdown:",
    ]
    for dimension in weights:
        b = breakdown[dimension]
        lines.append(
            f"  {dimension}: value {b['value']:.2f} x weight {b['weight']:.2f}"
            f" = {b['contribution']:.2f}"
            f" (confidence {b['confidence']:.2f}, source {b['source'] or 'unknown'}"
            + (f", aged x{b['aged']:.2f}" if b["aged"] is not None else "")
            + ")"
        )
    if flags:
        lines.append("Warnings: " + "; ".join(flags))
    return "\n".join(lines)
