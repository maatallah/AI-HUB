# POST-V1 ADAPTIVE ROUTING — M4 SCOPE SPECIFICATION

Status: **PLANNING DOCUMENT** (scope/architecture only — no implementation performed or authorized)
Baseline inspected: `061c8eb50ff48c5cf5217f234fbed48b47846e22` ("Close M3 post-v1 adaptive routing")
Parent (of this scope commit): `061c8eb…` (M3 closure record)
Date: 2026-08-29
Nature: Milestone scope definition for the **post-M3 configuration/version alignment (P1)** —
restoring `decision_version = "3.1.0"` as the effective runtime value across all routing surfaces.
**Not** an implementation authorization. No source, schema, configuration, test, or database artifact
was created or modified. This file is the only artifact produced by the M4 scoping effort.

Governing documents:

* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` — approved decision record; decision-version
  governance and the article/invariant constraints binding on M4
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — normative contract; §15 (versioning;
  `decision_version` bumps and traceability; `contract_version == "1"` additive-evolution rule)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M3-SCOPE.md` (`c54a585`) — M3 scope authority (R2 raised the
  code default to `3.1.0`)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M3-CLOSURE.md` (`061c8eb`) — M3 closure record
* M4 Discovery Report (owner-reviewed 2026-08-29) — established the P1, reproduced the runtime
  consequence, mapped the CLI/adapter/MCP divergence, and bounded the remediation

---

## 1. Purpose

Define the implementation slice (M4) that resolves the **post-M3 configuration/version drift (P1)**:

M3 (R2) canonically bumped `recommendation.decision_version` `3.0.0 → 3.1.0` in `app/config.py`
(`DEFAULT_CONFIG`). The tracked operational configuration `config.toml` and the template
`templates/config.toml` were **not** updated and still declare `decision_version = "3.0.0"`.
Because `load_config()` (app/config.py) deep-merges the repository `config.toml` **over**
`DEFAULT_CONFIG`, the tracked `3.0.0` overrides the M3 canonical `3.1.0` in every runtime artifact
that consults the effective configuration (CLI `route decide` envelopes and RECORD persistence).

M4 realigns the tracked configuration (and its template mirror) with the M3 canonical version so the
effective runtime decision version is `3.1.0` everywhere it is surfaced, with zero change to M3
runtime behavior.

Everything here is scope definition. Implementation requires a separate explicit owner mandate
(Section 11).

## 2. Current Baseline

* Branch `main`, HEAD `061c8eb…` (M3 closure), working tree clean except one pre-existing untracked
  file (`docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`); `main` ahead of `origin/main` by 10
  commits — nothing pushed.
* M1 complete and closed; M2 complete and closed (`2999a63` → `0fb771c` → `2738757a`); M3 complete
  and closed (`c54a585` → `a6846de` → `061c8eb`).
* Full Python baseline: **548 passed**; routing/decision subset: **115 passed** (independently
  verified during the post-M3 functional acceptance drive).
* Verified facts underpinning M4:
  * `app/config.py:62` (`DEFAULT_CONFIG`) → `"decision_version": "3.1.0"` — canonical code default.
  * `config.toml:42` → `decision_version = "3.0.0"` — **stale operational configuration (P1)**.
  * `templates/config.toml:34` → `decision_version = "3.0.0"` — **stale template mirror (P1)**.
  * `load_config()` merges repo `config.toml` over `DEFAULT_CONFIG` (highest-precedence operational
    file) — verified empirically (`config show` → `3.0.0`).
  * CLI `route decide` and RECORD report/persist `3.0.0` (via `load_config()` → `DecisionPolicy`).
  * Adapter and MCP report `3.1.0` (they use `DEFAULT_POLICY`, i.e. code defaults — see D2 ruling).
  * `contract_version == "1"`; no `max_cost`; no schema/event/`_sort_key` change involved.

## 3. M4 Objective

Deliver, behind one reviewable gate, the **post-M3 configuration/version alignment**:

1. Update the tracked operational `config.toml` so the effective runtime (and template) decision
   version is `3.1.0` — the M3 canonical version — and no longer `3.0.0`.
2. Update `templates/config.toml` to the same value to preserve the documented two-file
   configuration alignment convention (`config.toml` == `templates/config.toml`).
3. Verify, via the acceptance criteria in Section 9, that every routing surface surfaces `3.1.0`
   (CLI DECIDE, RECORD persistence, adapter, MCP) while every M3 invariant holds unchanged.

M4 is complete when every acceptance criterion in Section 9 passes on a clean tree and the
implementation diff is limited to the authorized file list (Section 11).

## 4. Owner Rulings (recorded 2026-08-29)

* **Canonical `decision_version` = `3.1.0`** — confirmed as the authoritative post-M3 version.
* **D2 (adapter/MCP policy sourcing):** adapter and MCP **remain on their existing code-default
  policy sourcing** for M4. `connectors/adapter.py` and MCP policy sourcing are **not** modified.
  The known CLI-vs-connector divergence on the remaining policy knobs (default_profile, aging days,
  derive_operational, max_chain_length) is **out of M4 scope** and deferred to a future ruling.
  M4 only guarantees version-value consistency (`3.1.0`) across surfaces.
* **Both configuration files are in scope:** `config.toml` and `templates/config.toml`.
* **Candidate B (regression protection):** recommended but **optional**. M4 scope is **not** expanded
  merely to add tests; any regression test requires separate owner authorization.
* **Candidate D** (broader routing capabilities) remains **deferred/out of scope**.
* M1/M2/M3 implementation and governance artifacts remain **immutable**.

## 5. M4 Required Scope

| # | Item | Contract/Type ref | Notes |
|---|------|-------------------|-------|
| R1 | Effective default configuration reports `3.1.0` | §15 | `config show` prints `decision_version = "3.1.0"`; `config validate` passes; `load_config().recommendation_decision_version == "3.1.0"` |
| R2 | Tracked configuration no longer overrides the canonical version | §15 | `config.toml` `[recommendation] decision_version` `3.0.0 → 3.1.0` |
| R3 | Template configuration aligned | config convention | `templates/config.toml` `[recommendation] decision_version` `3.0.0 → 3.1.0`, preserving the documented mirror convention |
| R4 | CLI `route decide` emits `3.1.0` | §15 | envelope `policy.decision_version == "3.1.0"` (traced `load_config → DecisionPolicy.from_config → policy_echo`) |
| R5 | RECORD persists `3.1.0` | §15 | `recommendation rows. decision_version == "3.1.0"` on `route record` (temp DB) |
| R6 | Adapter and MCP report `3.1.0` | §15 | `route_decide` / `route.decide` `policy.decision_version == "3.1.0"`, consistent with CLI; no regression from today's `3.1.0` (unchanged code-default path per D2) |
| R7 | `contract_version == "1"` unchanged | contract §15 | envelope `contract_version` remains `"1"` |
| R8 | M3 cost semantics and ordering unchanged | contract §7 | golden candidate ordering identical; `_sort_key` untouched; no algorithm/source edit |
| R9 | DECIDE zero-write / RECORD explicit append-only preserved | contract Art. 7/10 | DECIDE fingerprint unchanged (no writes); RECORD remains the single explicit append-only persistence path |

## 6. Deferred Scope (explicitly out of M4)

* **D2 connector policy-sourcing unification** (adapter/MCP consulting the effective configuration) —
  deferred pending a future owner ruling; explicitly **not** in M4.
* Candidate D routing capabilities: `max_cost` enforcement; contradictory-evidence detection;
  region/residency and deadline constraints; per-model availability overrides; ADR-0004
  point-in-time snapshots; runtime feedback / telemetry / review queueing; HTTP/gateway surface;
  execution/proxying/retries/streaming.
* Regression test (Candidate B) unless separately owner-authorized.

## 7. Explicit Non-Goals

No modification to `connectors/adapter.py` or MCP policy sourcing (D2 ruling). No Python source
change of any kind (`app/config.py` stays `3.1.0`). No schema, `EVENT_TYPES`, migration, dependency,
credential, or database-data change. No test change. No CHANGELOG/handover modification during the
scope phase. No new routing capabilities, no architecture change, no adaptive behavior, no new APIs
or server surfaces. No M1/M2/M3 artifact alteration.

## 8. Integration Points (existing, verified)

| Existing interface | Used by M4 |
|---|---|
| `app/config.py::load_config` / `DEFAULT_CONFIG` | effective config source; R1 verification |
| `config.toml` (`[recommendation].decision_version`) | R2 alignment target (line 42) |
| `templates/config.toml` (`[recommendation].decision_version`) | R3 alignment target (line 34) |
| `recommendation/decision.py` (DecisionPolicy.from_config, policy_echo, RECORD) | R4–R6/R9 verification surface; unchanged |
| `connectors/adapter.py` / MCP `route.decide` | R6 verification surface; **unchanged** (D2) |
| `app/main.py cmd_route` (`route decide` / `route record`) | R4/R5 verification surface; unchanged |

## 9. Acceptance Criteria (objectively verifiable)

1. `config show` → `decision_version = "3.1.0"`; `config validate` → valid; `load_config()`
   returns `recommendation_decision_version == "3.1.0"`.
2. `config.toml` and `templates/config.toml` both contain `decision_version = "3.1.0"` and no
   `3.0.0` version string in the `[recommendation]` section.
3. CLI `route decide --json` envelope `policy.decision_version == "3.1.0"`; `route record` on a temp
   DB persists `3.1.0` in `recommendations.decision_version`.
4. Adapter `route_decide` and MCP `route.decide` report `3.1.0` (unchanged code-default path), and
   no surface reports `3.0.0`.
5. `contract_version == "1"` in every envelope.
6. M3 golden candidate ordering identical; `_sort_key`/algorithm files byte-identical vs
   `a6846de`.
7. DECIDE zero-write fingerprint unchanged; RECORD append-only behavior unchanged.
8. Full pre-existing suite green (548 Python + targeted config/decision/adapter/MCP; no test
   change required).
9. `git diff --name-only` for the implementation commit restricted to the authorized file list
   (Section 11) plus the M4 closure record; M1/M2/M3 SHAs unchanged; nothing pushed.

## 10. Compatibility / Hard Invariants

* `contract_version` stays `"1"`; evolution additive-only within v1 (§15).
* DECIDE remains zero-write; RECORD remains the single explicit append-only persistence path.
* Provenance integrity preserved (column/row structure untouched; the persisted *value* becomes
  `3.1.0` from configuration — no schema change).
* Deterministic/reproducible behavior preserved (same-instant determinism, Article 7).
* No credentials; no execution/proxying; no autonomous provider mutation; no adaptive behavior.
* No schema/`EVENT_TYPES`/dependency change.
* M1/M2/M3 implementation and governance artifacts immutable and untouched.

## 11. Implementation Authorization Boundary & File List

This scope document authorizes **nothing** — no code, no tests, no configuration edit beyond this
planning artifact. Implementation requires a separate explicit owner mandate. The implementation
commit must satisfy the following **explicit M4 file-boundary authorization**:

**Required files (M4 core — configuration alignment only):**

* `config.toml` — `[recommendation] decision_version` `3.0.0 → 3.1.0` (R2) only.
* `templates/config.toml` — `[recommendation] decision_version` `3.0.0 → 3.1.0` (R3) only.

This is not general permission to modify either file.

**Optional (only if separately owner-authorized; Candidate B):**

* A focused regression test asserting the shipped/effective config cannot silently override the
  canonical `3.1.0`. M4 scope is not expanded merely to add tests.

**Closure artifact (separate closure step, not the implementation commit):**

* `docs/review/POST-V1-ADAPTIVE-ROUTING-M4-CLOSURE.md` (M4 closure record, mirroring M1/M2/M3).

**Exact forbidden files/areas for M4:**

* `connectors/adapter.py`, `connectors/mcp/*.py` — **forbidden** (D2 ruling; no policy-sourcing change).
* `app/config.py`, `recommendation/*`, `database/*`, `schema.sql` — forbidden (no source/schema change).
* `config.toml` / `templates/config.toml` **outside** the single `recommendation.decision_version`
  value — forbidden.
* Tests (unless Candidate B separately authorized) — forbidden.
* `CHANGELOG.md`, `handover/*` — forbidden for M4 core unless a separate owner decision adds a
  governance record.
* All M1/M2/M3 documents — forbidden (immutable).
* All Candidate D capabilities — forbidden.

Dependent manifest/coverage expansions beyond this list (if any) require the same owner-authorized
expansion process used in M2/M3 — never silently.

## 12. Governance / Authorization Boundary

* M4 implementation is separated from this scope by a review gate and a separate explicit
  implementation authorization (the M1/M2/M3 discipline).
* M4 scope definition approval does not constitute implementation authorization.
* M1, M2, and M3 artifacts are immutable; neither is altered by this scope.
* Nothing may be pushed without separate authorization.

---

## 13. Verification Strategy (for the M4 implementation phase)

1. **Configuration-level:** `config show` → `3.1.0`; `config validate` → valid; both `.toml` files
   verified at `3.1.0`.
2. **CLI:** `route decide --json` envelope `3.1.0`; `route record` (temp DB) persists `3.1.0`.
3. **Adapter/MCP:** `route_decide` / `route.decide` report `3.1.0`; no surface reports `3.0.0`.
4. **Regression:** full 548 Python suite + targeted config/decision/adapter/MCP tests green.
5. **M3 invariants:** `contract_version == "1"`; golden ordering unchanged; no algorithm/schema diff.
6. **Repository integrity:** M1/M2/M3 SHAs unchanged; clean tree; nothing pushed.

---

*End of scope document. Planning only — no implementation was started, and no production file was
touched. `config.toml` and `templates/config.toml` remain unmodified at `3.0.0`; D2 is honored
(no adapter/MCP policy sourcing change); `max_cost` and Candidate D capabilities are excluded.*