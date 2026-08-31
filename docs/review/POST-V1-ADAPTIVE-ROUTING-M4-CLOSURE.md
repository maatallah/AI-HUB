# POST-V1 ADAPTIVE ROUTING — M4 CLOSURE RECORD

Status: **M4 ACCEPTED / CLOSED**
Milestone Scope: `docs/review/POST-V1-ADAPTIVE-ROUTING-M4-SCOPE.md` (owner-approved 2026-08-29; committed as governance artifact)
Scope Commit: *(separate dedicated commit, matching M2/M3 convention)*
Milestone Commit: `1a465f384071f5eca361463fd97037b93a3998b1` ("Implement post-v1 adaptive routing M4")
Parent of Implementation: `061c8eb50ff48c5cf5217f234fbed48b47846e22` ("Close M3 post-v1 adaptive routing")
Date: 2026-08-29
Audit Verdict: **M4 ACCEPTED** (R1–R9 PASS; hard invariants PASS; boundary/governance audit PASS)
Owner Rulings (2026-08-29): canonical `decision_version = "3.1.0"`; **D2** = adapter/MCP remain on
code-default policy sourcing (no change); both configuration files in scope; **Candidate B** optional/unauthorized;
**Candidate D** deferred/out of scope.

Governing documents:
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M4-SCOPE.md` — M4 scope authority (owner-approved as written)
* M4 Discovery Report (owner-reviewed 2026-08-29) — established the P1 and the CLI/adapter/MCP surface picture
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M3-SCOPE.md` (`c54a585`) and M3 CLOSURE record (`061c8eb`) — M3 binding
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` and `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — governance & contract

---

## 1. M4 Objective & Summary

Resolve the **post-M3 configuration/version drift (P1)**: M3 (R2) canonically bumped
`recommendation.decision_version` to `3.1.0` in `app/config.py` (`DEFAULT_CONFIG`), but the tracked
operational configuration and its template mirror were never aligned and still declared `3.0.0`.
Because `load_config()` deep-merges the repo `config.toml` over `DEFAULT_CONFIG`, the stale `3.0.0`
overrode the canonical `3.1.0` in the effective configuration, CLI `route decide` envelopes, and
RECORD persistence.

### Implementation Summary

* **R2 — `config.toml`:** `[recommendation] decision_version` `3.0.0 → 3.1.0` (single value).
* **R3 — `templates/config.toml`:** `[recommendation] decision_version` `3.0.0 → 3.1.0` (single value).
* No other content in either file was modified. No Python source, adapter/MCP, test, schema, database,
  dependency, CHANGELOG, or handover file was touched.

### Authorized Files (exact two-file implementation boundary)

`config.toml` (R2 value only) and `templates/config.toml` (R3 value only). Commit diff:
**2 files changed, 2 insertions(+), 2 deletions(-)** — nothing else.

---

## 2. Milestone Invariants & Boundary Compliance

* **CONTRACT VERSION PRESERVED:** `contract_version` stays `"1"` (verified in core and CLI envelopes).
* **DECIDE ZERO-WRITE:** DECIDE wrote no rows — `recommendations` fingerprint unchanged (0 → 0) on a
  populated temp DB; RECORD remains the single explicit persistence path.
* **RECORD EXPLICIT / APPEND-ONLY:** `record_decision` appended exactly `count` rows (0 → 1) and
  persisted `decision_version = "3.1.0"`.
* **PROVENANCE INTEGRITY:** schema/DDL untouched; only the persisted *value* changed via configuration.
* **DETERMINISM / M3 COST SEMANTICS:** repeated DECIDE produced identical candidate ordering; `_sort_key`
  and all algorithm files byte-identical; golden ordering tests green.
* **`max_cost` EXCLUDED:** not implemented (absent from the diff and the repository source).
* **NO SCHEMA / NO EVENT-LOG / NO DEPENDENCY / NO CREDENTIAL / NO EXECUTION CHANGES.**
* **D2 NOT IMPLEMENTED:** `connectors/adapter.py` and MCP policy sourcing are unmodified (code-default
  policy sourcing retained by owner ruling).
* **CANDIDATE B NOT IMPLEMENTED:** no regression test added (remains unauthorized/optional).
* **CANDIDATE D NOT IMPLEMENTED:** `max_cost`, contradictory evidence, region/residency, deadlines,
  per-model availability, ADR-0004 snapshots, feedback/telemetry, review queues, HTTP/gateway,
  execution/proxying, credentials, and autonomous provider mutation all remain deferred/out of scope.
* **M1/M2/M3 IMMUTABLE:** no M1/M2/M3 artifact changed; SHAs unchanged.

---

## 3. Verification & Test Suite Result

* **Configuration-level:** `config show` → `decision_version = "3.1.0"`; `config validate` → valid;
  `load_config().recommendation_decision_version == "3.1.0"`.
* **Runtime surfaces (temp DB, artifacts removed afterward):**
  * CLI `route decide --json` → `policy.decision_version = "3.1.0"`, `contract_version = "1"`.
  * RECORD persisted `recommendations.decision_version = "3.1.0"` (all rows).
  * Adapter `route_decide` → `"3.1.0"`; MCP `route.decide` → `"3.1.0"`.
  * No routing surface reported `3.0.0`.
* **End-to-end checks:** DECIDE envelope status `OK`; zero-write fingerprint unchanged; append-only
  RECORD; deterministic candidate ordering; adapter/MCP consistency.
* **Regression suite:** `py -m pytest tests -q` → **548 passed, 0 failed, 0 skipped** (single
  uninterrupted full-suite run in 2078.61s / 0:34:38). The 548-test baseline matches the M3-closure
  figure; the two-file configuration alignment adds no tests and changes no expectations.
* **R1–R9 audit:** all nine requirements verified and **PASS** against the M4 scope authority.

---

## 4. Milestone Review Verdict

* **M4 ACCEPTED** via owner review of `1a465f3`.
* R1–R9: **PASS** (effective config `3.1.0`; tracked config no longer overrides; template aligned;
  CLI DECIDE `3.1.0`; RECORD persists `3.1.0`; adapter/MCP `3.1.0`; `contract_version` `"1"`; M3 cost
  ordering unchanged; DECIDE zero-write / RECORD append-only preserved).
* Hard invariants and boundary audit: **PASS** — the implementation diff is restricted to the two
  authorized configuration files; `1a465f3^ = 061c8eb` (M3 closure baseline); D2/Candidate B/Candidate
  D and all source/schema/database/dependency changes absent.

---

## 5. Formal Closure Declaration

**Milestone M4 is ACCEPTED and CLOSED.**

The post-M3 configuration/version drift (P1) is resolved: the effective runtime decision version is
`3.1.0` across CLI, RECORD, adapter, and MCP, with every M3 invariant preserved.

This closure record is a governance artifact distinct from the implementation commit `1a465f3`, which
remains unchanged and unamended. M4 implementation and closure are separate steps. No further code,
test, or configuration changes are authorized under M4. D2 unification, Candidate B (regression
protection), Candidate D capabilities, and all other deferred scope remain explicitly excluded,
pending future owner ruling.
