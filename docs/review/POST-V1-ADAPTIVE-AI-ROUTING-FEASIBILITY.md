# POST-V1 ADAPTIVE AI ROUTING — FEASIBILITY / DESIGN SPIKE

Status: **READ-ONLY INVESTIGATION REPORT** (uncommitted working document)
Baseline inspected: `origin/main` = `2bed04252b257b243a996b25d18ef4855053fae6` (Phase 6 released and closed)
Date: 2026-08-21
Nature: Feasibility/design spike. **Not** Phase 7. Not an implementation authorization.
No source code, specification, schema, or configuration was modified. This file is the only artifact created.

---

## 1. Executive Summary

AI-Hub already computes, explains, records and exposes (read-only) exactly the decision object that
"adaptive routing" needs: a deterministically ranked primary + fallback chain with per-dimension
scores, confidence, flags and provenance. What it does not yet have is a **stable, versioned,
machine-consumable routing decision contract** that an external execution layer (application,
gateway, agent runtime) can consume at the moment an AI request is made.

The investigation finds:

* The intelligence plane is complete for this purpose (verified in code, not inferred from
  filenames): ranking (`recommendation/engine.py`), chain construction (`fallback/engine.py`),
  explanation (`recommendation/explain.py`), provenance (`recommendation/provenance.py`),
  monitoring-derived operational scores (`scoring/derive.py`), read-only exposure via the shared
  adapter (`connectors/adapter.py`) and MCP tools (`connectors/mcp/tools.py`).
* The gap is small and well-bounded: constraint expressiveness beyond context/capabilities, a
  serialized decision envelope with explicit failure states, policy/version echo, and a sanctioned
  read-only "decide" surface (CLI JSON + MCP tool + adapter function).
* The execution boundary must remain: **AI-Hub = decision plane; application/gateway = execution
  plane**. Option C (execution gateway) is constitutionally incompatible (Articles 2, 6, 7) and is
  rejected. Option B (optional routing adapter) is deferred, not part of the first milestone.
* A feedback loop is possible without violating any constitutional principle **if** telemetry lands
  as review-gated evidence and never mutates scores automatically.
* Cost intelligence is achievable without credentials using only legitimately supplied evidence
  (declared prices, user-reported spend, benchmark data) — but one real semantic inconsistency in
  the current cost handling must be resolved first (Section 9).

**Verdict: CONDITIONAL GO** (Section 16). Recommended next milestone: **Routing Decision Contract +
Read-Only Decision API** (Section 12), documentation-first per Constitution Article 11.

---

## 2. Current AI-HUB Capability Baseline

All statements below were verified by reading the actual code at `2bed042`. Line references are to
the current working tree (identical to `origin/main`; tree was clean at inspection time).

### 2.1 Registry / provider / model representation

* `database/schema.sql` defines: `providers` (lifecycle CHECK: NEW/EVALUATING/ACTIVE/LIMITED/
  DEGRADED/OFFLINE/ARCHIVED), `models` (context_window, supports_tools/streaming/json/vision;
  legacy scalar score columns retained but superseded by `scores`, ADR-0001), `scores`
  (per-dimension value/confidence/source/scored_at; source CHECK = MANUAL/BENCHMARK/AUTOMATED_TEST/
  USER_FEEDBACK/OFFICIAL_INFORMATION), `availability` (state, consecutive_failures, quota_type,
  reset_at, last_success/last_failure), `events` (append-only), `preferences` (typed KV; custom
  profiles), `recommendations` (provenance), `discovery_candidates`, `benchmark_runs`,
  `benchmark_results`.
* `core/providers.py`: manual registry with `LEGAL_TRANSITIONS` (v1.2 §5 table),
  `STATUSES_REQUIRING_REASON`, archive-with-reason, every mutation emits an event.
* `core/models.py`: governed model operations (`add_model`, `get_model`, `list_models`,
  `update_model`, `archive_model`). Archival is event-only ("Option A"): rows are never altered or
  deleted; no model lifecycle state exists.

### 2.2 Monitoring

* `monitoring/health.py::check_provider`: HEAD-request reachability probe against `providers.base_url`;
  injectable transport; **no auth headers, no secrets, no payloads**; UNKNOWN when base_url absent
  (Article 10); emits HEALTH_CHECK_OK/FAILED/UNKNOWN with latency_ms.
* `monitoring/availability.py`: `update_availability` (success resets failures; failure increments),
  `apply_lifecycle` (legal transitions only; automatic ARCHIVED refused — Article 1); monitoring
  changes status only through `core.providers.update_provider`.
* `monitoring/quota.py`: `record_quota_signal` (ACTIVE→LIMITED on quota signal),
  `set_quota_reset` / `detect_quota_reset` (LIMITED→ACTIVE), `classify_status_code` (429 → rate).
  Note: these are library functions; **no CLI command exposes them today**.
* Lifecycle automation loop exists only inside the one-shot CLI run (`app/main.py::_monitor_run` +
  `_apply_monitoring_lifecycle`): ACTIVE→DEGRADED→OFFLINE after configured consecutive failures.
  There is **no daemon/scheduler** (consistent with Phase 6 D-P7: on-demand only).

### 2.3 Scoring

* `scoring/engine.py::effective_score`: stored score from `scores` (ADR-0001) with v1.2 §4 aging
  multipliers (fresh 1.00 / aging 0.90 / old 0.75 / stale 0.50) applied to confidence.
* `scoring/derive.py`: operational dimensions derived **at read time**, never stored:
  availability (state→100/70/40/0), reliability (100 − 20×consecutive_failures), latency (linear vs
  `latency_threshold_ms` from latest HEALTH_CHECK_OK event), context_window (linear to 131072).
  Missing inputs yield None — never fabricated (Article 10). `DERIVED_DIMENSIONS =
  ("availability", "reliability", "latency", "context_window")` — **cost and stability are not derived**.
* `scoring/ingest.py::set_score`: validated upsert (value 0–100, confidence 0–1, allowed sources)
  emitting SCORE_RECORDED/SCORE_UPDATED.

### 2.4 Recommendation

* `recommendation/engine.py::recommend`: deterministic pipeline — profile weights → eligibility
  filter (`ELIGIBLE_STATUSES = ACTIVE/LIMITED/DEGRADED`; min_context_window; required_capabilities
  mapped to supports_* columns) → effective scores per dimension → final = Σ weight×value →
  confidence = weight-weighted mean confidence → flags (degraded provider, insufficient data) →
  `_sort_key` implements v1.2 §7 Step 4 exactly: final desc, availability desc, reliability desc,
  cost asc, latency asc, model_identifier asc. Missing dimensions contribute 0 and are flagged.
* `recommendation/profiles.py`: four built-ins (coding/reasoning/free/long_context) with exact
  weights summing to 1.0; custom profiles stored as JSON under `profile.<name>` in `preferences`;
  weights validated at load (no hidden weighting).
* `recommendation/explain.py::build_explanation`: what / why / evidence / confidence text
  (Article 4).
* `recommendation/provenance.py::record_recommendation`: writes a `recommendations` row (UUID id,
  task, profile, provider/model ids, decision_version, score_breakdown JSON incl. per-dimension
  weight/value/contribution/confidence/source, explanation, confidence) + RECOMMENDATION_CREATED
  event. UUID identifies the record; content stays deterministic (documented Article 7 exception).

### 2.5 Fallback

* `fallback/engine.py`: `Chain` (primary + ordered fallbacks); `build_chain` = deterministic
  ranking truncated to eligible entries (max_chain_length+1); `select_fallback(conn, chain,
  current_provider_id)` walks the chain after the current position, prefers ACTIVE/LIMITED, uses
  DEGRADED only as flagged last resort, returns None when exhausted, and emits FALLBACK_TRIGGERED /
  FALLBACK_RECOVERED events; `check_recovery` returns the primary when eligible again.
* Eligibility derives solely from persisted state (`providers.status`); fallback never probes
  providers and never modifies lifecycle (v1.2 §7/§9).
* Important precision: `select_fallback`/`check_recovery` are **library functions requiring an open
  DB connection**; they write events by default. No CLI command and no connector currently invokes
  them. There is no runtime consumer of fallback selection anywhere in the repository.

### 2.6 Events / history / trend / benchmark

* `core/events.py`: append-only log; fixed `EVENT_TYPES` set (27 types spanning registry,
  monitoring, scoring, recommendation, fallback, discovery, benchmark). Unknown type → error.
* `dashboard/history.py`: score and availability series reconstructed read-only from events;
  docstring notes point-in-time snapshots remain deferred pending ADR-0004.
* `trend/analysis.py`: read-only direction/magnitude/stability per dimension series and per
  provider availability scalar; window anchored to most recent point (deterministic);
  `insufficient_data` below `min_points`; never writes, never fabricates.
* `benchmark/ingest.py`: provenance-aware import (content-hash dedupe, metric→(dimension, formula)
  mapping recorded on the run, raw values preserved in `benchmark_results`, normalized values
  mapped into `scores` with source=BENCHMARK).

### 2.7 Connectors / MCP / VS Code

* `connectors/adapter.py`: single stable **read-only** interface (8 functions incl.
  `recommend_top`, `fallback_chain`, `provider_status`, `model_scores`, histories); delegates to
  engines; returns plain dicts; performs no SQL of its own, no writes, no events, no provenance.
* `connectors/mcp/server.py`: bounded legacy-era stdio MCP server (Tools capability only;
  `PRAGMA query_only = ON` at the connection level). Modern era `2026-07-28` explicitly out of
  scope (spec §19.2.5, decision D-1).
* `connectors/mcp/tools.py`: seven fixed read-only tools, including `recommend_top` (explicitly
  does NOT record provenance) and `fallback_chain`.
* VS Code extension (`connectors/vscode/src/*`): presentation only; invokes read-only CLI commands
  (`features.ts` FEATURES list) and renders stdout verbatim; contains no decision logic.

### 2.8 Configuration & CLI surfaces

* `app/config.py`: TOML over documented defaults; **rejects any key resembling a credential**
  (`_reject_secrets`); URL safety validation for discovery allowlist; keys for monitoring thresholds,
  aging boundaries, `fallback.max_chain_length`, `recommendation.default_profile`,
  `recommendation.decision_version` (default "3.0.0"), discovery/benchmark/trend.
* `app/main.py` CLI (all synchronous one-shot processes): init-db, config show/validate, provider
  add/list/update/archive, monitor run/status/validate, score list/set, recommend top/chain,
  fallback status, dashboard status/report/history, discovery import/run/list/approve/reject,
  benchmark import/list, model list, trend scores/availability. **No `route` command, no quota
  command, no feedback-ingestion command exists.**

### 2.9 What does NOT exist (verified absences)

No HTTP/API server mode (the only long-lived process is the stdio MCP server). No inference/request
proxying of any kind. No credential storage or retrieval. No scheduler/daemon. No runtime outcome
telemetry ingestion. No cost derivation. No point-in-time snapshots (ADR-0004 reserved/deferred).
No machine-readable (JSON) recommendation output — CLI output is human-readable text; structured
output exists only inside the adapter/MCP path as ad-hoc dicts.

---

## 3. Existing Components Reusable for Routing

| Routing need | Existing component | Reuse classification |
|---|---|---|
| Candidate universe | `models` ⋈ `providers` via `recommendation.engine._eligible_models` | **Reusable unchanged** |
| Eligibility (status/context/capabilities) | `ELIGIBLE_STATUSES`, `min_context_window`, `required_capabilities` | **Reusable unchanged** |
| Deterministic ranking | `recommend()` + `_sort_key` (v1.2 §7 Step 4) | **Reusable unchanged** |
| Fallback chain | `fallback.build_chain` / `Chain` | **Reusable unchanged** |
| Rationale & confidence | `build_explanation`, `Recommendation.confidence/breakdown/flags` | **Reusable unchanged** |
| Provenance / decision ID | `record_recommendation` (UUID + decision_version + breakdown) | **Reusable unchanged** (opt-in) |
| Operational freshness | `scoring.derive` (availability/reliability/latency/context_window at read time) | **Reusable unchanged** |
| Read-only exposure channel | `connectors.adapter` + MCP tools pattern | **Reusable pattern; new thin functions** |
| Structured serialization | `asdict(Recommendation)` used by adapter/MCP | **Small extension** (envelope around it) |
| Constraint set | only `min_context_window`, `required_capabilities` | **Small extension** (see §4) |
| Failure/no-decision states | empty result prints text; no typed states | **Genuinely new** |
| Policy/version echo | `decision_version` in config/provenance; profile weights recoverable from breakdown | **Small extension** (explicit echo field) |
| Execution of requests | none (by design) | **Intentionally out of scope** |

---

## 4. Gap Analysis

Target capability: *"Given a task and constraints, return a routing decision."*

### 4.1 Already implemented (verified)

Ranking, eligibility filtering, deterministic ordering, chain construction, explanation,
confidence, flags, provenance recording, monitoring-derived operational dimensions, read-only
adapter/MCP exposure. A consumer can *today* call `adapter.fallback_chain(conn, task, profile)`
and receive a structured primary + fallbacks payload.

### 4.2 Reusable with small extensions

1. **Constraints.** `recommend()` accepts only `min_context_window` and `required_capabilities`.
   Real routing constraints (max price, allowed/denied providers or models, required region/data
   residency, budget ceiling, deadline/latency class) do not exist. Extension point: a constraints
   object passed into `_eligible_models` as additional pure filters. This preserves determinism
   (filters remain functions of persisted state + supplied arguments).
2. **Decision envelope.** `Chain`/`Recommendation` serialize via `asdict`, but there is no single
   versioned object that also carries: constraints echo, resolved profile weights, policy
   (decision_version, aging parameters, max_chain_length), computation timestamp, decision identity,
   and typed failure states. This is additive composition, not engine change.
3. **Sanctioned decide surface.** `recommend_top` (MCP/adapter) deliberately skips provenance;
   the CLI `recommend top` records it but prints text. A routing API needs one explicit function
   that composes `recommend`/`build_chain` + optional `record_recommendation` and returns the
   envelope — with recording strictly opt-in, mirroring existing semantics.
4. **Provenance for chains.** `recommendations` rows record individual ranked candidates (the CLI
   records each result), but there is no record that binds *a chain* (primary + ordered fallbacks +
   constraints) as one decision. Either the envelope carries enough to reconstruct the chain from
   candidate rows, or a chain-level record is added later (spec decision, not needed for MVP if the
   envelope echoes everything).

### 4.3 Genuinely new capability

* **Typed failure/unknown states**: NO_CANDIDATE (no eligible model), INSUFFICIENT_DATA (candidates
  exist but flagged dimensions missing), CONSTRAINT_UNSATISFIABLE. Today these collapse into "No
  eligible recommendations." text or silent flags. Article 10 requires unknowns be explicit — a
  contract must make them first-class.
* **Machine-readable output on the CLI** (JSON mode) — all current CLI output is human text.
* **A versioned public contract** (schema + stability rules) that external layers can rely on.
  Nothing in the repo today promises shape stability across versions; `decision_version` covers
  logic versioning, not wire format versioning.

### 4.4 Intentionally out of scope (existing decisions — not gaps)

Request execution/proxying (never built; health checks are metadata-only HEAD probes);
credential custody (Article 6, spec §11); scheduling/daemon (D-P7); modern MCP era (D-1, §19.2.5);
workspace/project discovery (ADR-0003, D-P5); automatic archival (Article 1).

---

## 5. Proposed Routing Decision Model (conceptual, implementation-neutral)

> Design proposal only. Nothing below is implemented; no schema migration is proposed. Field names
> are illustrative; the governing spec (Article 11) would fix them.

```text
RoutingDecision (versioned envelope, e.g. schema_version = "1")
├── decision_id            : opaque id, present ONLY when the caller opted to record provenance
├── created_at             : computation timestamp (UTC)
├── request
│   ├── task               : free-text task descriptor (as supplied)
│   ├── profile            : profile name
│   └── constraints        : EXACTLY what was supplied (echo; unknown/absent = null, never implied)
├── policy                 : everything needed to reproduce the decision
│   ├── decision_version   : from config (logic version)
│   ├── contract_version   : wire-format version of THIS envelope
│   ├── resolved_weights   : dimension → weight actually applied (built-in or custom)
│   ├── max_chain_length, aging params, latency_threshold_ms, derive_operational
├── candidates[]           : full deterministic ranking (may be truncated by limit; total_count kept)
│   └── { provider_id, provider_name, model_id, model_identifier,
│         final_score, confidence,
│         breakdown: { dimension: {value, weight, contribution, confidence, source, aged} },
│         flags[], rank }
├── selected               : candidates[0] reference (or null)
├── fallback_chain[]       : ordered references after primary (eligibility-filtered)
├── rationale              : human-readable explanation (what/why/evidence/confidence)
└── status                 : OK | NO_CANDIDATE | INSUFFICIENT_DATA | CONSTRAINT_UNSATISFIABLE
    └── status_detail      : e.g. missing dimensions, unsatisfiable constraint names
```

Design properties and how they map to existing verified behavior:

* **Determinism**: identical DB state + identical request ⇒ identical `candidates`, order, scores
  (pure functions in `recommendation/engine.py`, `fallback/engine.py`). Only `created_at` and the
  optional `decision_id` vary — mirroring the existing documented UUID exception (identity only).
* **Reproducibility**: `policy` echoes every parameter that influenced the result
  (`decision_version`, weights, aging windows, thresholds), so a consumer can re-run or audit.
  This generalizes what `score_breakdown` + `decision_version` already record per candidate.
* **Truthfulness**: absent evidence remains absent — dimensions with no data appear in `flags` /
  `status_detail`, never as fabricated values (already enforced in `scoring.derive` /
  `recommendation.engine`).
* **Failure states**: explicit, typed, non-fabricated (new, see §4.3).
* **Opt-in persistence**: recording provenance remains a separate, explicit act
  (`record_recommendation` semantics preserved); read paths stay read-only.

---

## 6. Intelligence Plane vs Execution Plane Boundary

Options evaluated:

**A. Return routing decisions only.**
Fully compatible. Precedent: Phase 5 connectors are read-only consumers of decisions; the adapter
docstring forbids mutation; MCP runs with `PRAGMA query_only`. A decision API is the same boundary,
one level more formal. No new security surface: no credentials, no provider traffic, no secrets.

**B. Provide an optional routing adapter (AI-Hub executes and reports back).**
Requires AI-Hub to hold or broker provider credentials (Article 6 violation as designed today —
§11 allows metadata only), introduces nondeterministic runtime state into a system whose value
proposition is reproducible decisions (Article 7), and converts "recommends, user decides"
(Article 2) into "acts, user observes". It would also couple AI-Hub to provider API churn
(Article 12 risk). **Deferred — not in the first milestone; revisit only behind an explicit ADR
with a credential-delegation design that keeps raw secrets out of AI-Hub storage.**

**C. Become an execution gateway.**
Rejected. Contradicts Articles 2, 6, 7 directly; duplicates the execution plane that gateways
already occupy (Section 11); maximizes coupling and liability; contradicts the mission statement
("help developers make informed decisions — not to automatically control their development
environment", START-HERE.md).

**Recommended position: A, deliberately narrower than B/C.** AI-Hub produces and explains decisions;
the application/gateway executes; observed results may return later as governed evidence (Section 8).
This is the same separation the project already practices: `monitoring/health.py` probes metadata
without credentials; connectors read without writing; discovery materializes only after human
approval.

Constitutional cross-check (detail in Section 15): A satisfies all twelve articles; B strains
2/6/7; C violates them.

---

## 7. Fallback Analysis

Question: is the deterministic fallback engine sufficient for *runtime* consumption?

**What exists (verified):**
* Chain construction is deterministic and eligibility-aware (`build_chain`).
* Next-hop selection logic exists and is deterministic (`select_fallback`: preferred-first walk
  after the current position; DEGRADED only as last resort; None when exhausted).
* Recovery detection exists (`check_recovery`).
* Selection/recovery emit append-only events (FALLBACK_TRIGGERED / FALLBACK_RECOVERED).

**What separates "calculates a chain" from "an external layer can safely consume it":**

1. **A serializable chain with explicit semantics.** Exists in memory (`Chain`/`Recommendation`);
   exposed ad-hoc via `adapter.fallback_chain`. The contract (Section 5) makes it stable and adds
   rank, eligibility state at computation time, and flags per entry.
2. **Freshness/TTL semantics.** A chain is a point-in-time function of `providers.status`,
   `availability`, and scores. Monitoring updates change eligibility continuously. An external
   consumer must know: re-query on every request (cheap — local SQLite reads) or treat the chain as
   valid for a bounded period. Today nothing expresses staleness. The contract should carry
   `computed_at` plus a documented freshness rule; AI-Hub should NOT embed a TTL policy silently.
3. **Advance-on-failure rules.** `select_fallback` answers "who is next after X" but the *trigger*
   (what counts as a failure worth advancing on) lives in the execution plane. The contract should
   document the intended consumer algorithm: try selected; on transport/auth/quota failure, advance
   to next chain entry; optionally report the signal back (Section 8). AI-Hub already has the
   vocabulary for signals (`quota.classify_status_code`, QUOTA_STATUS_CODES = 429).
4. **Write-path governance.** `select_fallback`/`check_recovery` mutate history (events) and have
   **no sanctioned caller** today. If a runtime layer invoked them directly, every retry would
   append events — uncontrolled write amplification into an append-only ledger. Resolution for the
   first milestone: keep runtime consumption **read-only** (consumer re-reads the chain; AI-Hub
   records nothing per-request). A gated write path for "report fallback used" belongs to the
   feedback design (Section 8), decided explicitly, not inherited implicitly.
5. **Exhaustion semantics.** `select_fallback` returning None is in-band; the contract's
   `status`/`status_detail` must expose chain exhaustion explicitly.

Conclusion: the engine is sufficient as the *decision core*. Runtime sufficiency requires only the
contract items above — no change to ranking or eligibility logic.

---

## 8. Feedback / Evidence Loop

Proposed loop: decision → execution (external) → observed outcome → evidence → future recommendation.

**Telemetry AI-Hub can safely accept** (all derivable from the executing side without secrets):
* decision reference (decision_id when provenance was recorded) and which chain entry was used;
* outcome class: success / failure / quota-limited / timeout;
* latency_ms of the attempt; timestamp;
* optionally self-reported token counts / cost when the executing application chooses to share them
  (source = USER_FEEDBACK or AUTOMATED_TEST — both already legal `scores.source` values).

**What AI-Hub must NOT collect:** prompts, completions, or any request/response content; provider
API keys or tokens (Article 6; `config._reject_secrets` precedent); repository code or workspace
content (Article 3); end-user identities; anything not needed as aggregate evidence.

**Conflict check with existing security model:** none, provided ingestion is metadata-only. The
repo already demonstrates the pattern: health checks carry latency/status only; benchmark imports
are secret-scanned (`benchmark.ingest._check_no_secrets`); discovery payloads are validated and
sanitized (`discovery.sources._check_no_secrets`, `sanitize_url`).

**Automatic vs governed score effects — must be governed.** Three reasons grounded in existing
principles and precedents:
1. Article 10: raw runtime outcomes are observations, not verified quality; converting them
   silently into dimension scores would present estimates as facts unless clearly sourced and
   aggregated.
2. Article 7: recommendations must remain pure functions of reviewed state; a live telemetry
   channel mutating `scores` mid-flight makes decisions depend on unreviewed runtime noise.
3. Project precedent: benchmark evidence (automated!) still enters through an explicit, hashed,
   mapped import; discovery (automated!) stops at PENDING_REVIEW until a human approves. Runtime
   telemetry deserves the same gate.

**Recommended shape (future milestone, not MVP):** outcomes land as append-only events (new
EVENT_TYPES, e.g. ROUTING_OUTCOME — note `core.events.EVENT_TYPES` is a fixed set, so this is a
spec-governed addition per Article 11) plus an explicit, reviewed aggregation step that *may*
produce USER_FEEDBACK-sourced score updates. Never a silent auto-mutation. Unknown/failed
observations produce no fabricated scores.

---

## 9. Cost Intelligence Analysis

Current state (verified):
* `cost` is a first-class profile dimension (free: 0.40, reasoning: 0.05, coding: 0.00) and appears
  in the sort key (`_sort_key`: cost ascending).
* `DERIVED_DIMENSIONS` excludes cost — nothing derives it. The only way to populate it today is the
  generic `score set --dimension cost ...` (manual) or a benchmark mapping.
* Automatic spend tracking was deliberately excluded because it requires credentials (quota module
  docstring; Phase 2 closure; Article 6).

Can useful routing-cost intelligence exist **without credentials**? Yes, from three legitimate
evidence classes, all already representable in the schema:
1. **Declared pricing** (published per-token/unit prices entered manually or imported like
   benchmarks, source = MANUAL/OFFICIAL_INFORMATION/BENCHMARK). Static, auditable, refreshable by
   re-import; supports a normalized 0–100 representation with a documented formula (mirroring
   `benchmark.ingest.FORMULAS` discipline).
2. **User-reported actual spend** (source = USER_FEEDBACK) from the executing application's own
   billing view — the user shares their own numbers; AI-Hub holds no keys.
3. **Derived proxies already present**: latency and availability trends (`trend/analysis.py`)
   partially proxy "operational cost of poor providers"; no fabrication required.

**Finding — semantic inconsistency to resolve before relying on cost for routing.** Scores are
defined on a 0–100 "higher is better" scale (`scoring.ingest._validate_value`), and the weighted
formula treats them that way (`final += weight × value`). But the fallback sort orders cost
**ascending** (`_sort_key`: lower cost value ranks earlier), i.e. it interprets a stored cost value
as a *price-like* quantity where lower is better. These two interpretations conflict: a cost value
that helps `final` (higher = better) hurts the tie-break sort (lower = better). With today's
built-in profiles (coding cost weight 0.00; free profile omits reliability... note free has no
reliability dimension and its cost weight 0.40 participates in `final`) the ambiguity is latent but
real. The governing spec for routing must define cost semantics once (recommended: store a
normalized 0–100 *affordability* score, higher = cheaper, and flip the sort key accordingly — or
store price and exclude it from the weighted sum). This is a small, well-contained decision but it
must be explicit (Articles 7, 11).

---

## 10. MCP / VS Code Integration Analysis

The conceptual operations map onto the existing bounded, read-only tool pattern with no protocol
change:

| Conceptual operation | Existing basis | Delta |
|---|---|---|
| recommend model | MCP tool `recommend_top` → `adapter.recommend_top` → `recommend()` | return the full decision envelope instead of bare list |
| explain decision | breakdown/explanation already in `Recommendation`; `list_recommendations` exists for recorded ones | small adapter getter by decision/provenance id |
| get fallback | MCP tool `fallback_chain` → `build_chain` | same envelope treatment |
| inspect provider state | MCP tool `provider_status` (+ `model_scores`, histories) | none |

Guardrails that keep this out of "unrestricted automation agent" territory (all consistent with
spec §19):
* Tools stay **read-only**; the server already enforces `PRAGMA query_only = ON`
  (`connectors/mcp/server.py::main`).
* No tool executes AI requests, holds credentials, or mutates settings — §19.5 guarantees extend
  verbatim.
* Any future feedback-submission tool is a *separate, explicitly gated* addition (new event types,
  spec section, tests) — never smuggled into the read-only tool set.
* VS Code remains presentation-over-CLI (`features.ts` pattern); a routing feature would simply add
  another read-only command rendering the decision envelope. No decision logic moves into the
  extension.
* Protocol scope stays bounded (legacy-era stdio, D-1). The contract rides in tool *results*, not
  in new protocol machinery.

---

## 11. Differentiation / Value Analysis

Would this make AI-Hub meaningfully different from "just use an AI gateway/router"? Yes — because
the proposed direction positions AI-Hub **above** the execution plane, not beside it:

* **Evidence-based, sourced, aged scoring** (scores carry value + confidence + source + scored_at;
  aging multipliers; benchmark lineage down to raw metric values) — gateways see only live traffic.
* **Deterministic, reproducible ranking with full provenance** (breakdown + decision_version +
  explanation recorded per decision) — gateway routing (retries, load-balancing, least-cost/heuristic
  picks) is typically opaque and non-reproducible by design.
* **Explanation as a first-class output** (Article 4) — a routing answer a developer can audit.
* **Review-gated ecosystem intelligence** (discovery candidates require human approval; benchmark
  imports are hashed and mapped) — no silent catalog drift.
* **Trend analysis over preserved history** (append-only events; direction/stability per dimension).
* **Human authority and local-first operation** (no daemon, no credential custody, offline-capable,
  stdio MCP) — trust posture gateways cannot offer since they must hold keys and serve traffic.

The two planes are complementary: a gateway could *consume* AI-HUB decisions (fetch chain, execute,
report outcomes). That integration story is itself the differentiator — AI-HUB becomes the
auditable brain that any executor can use, rather than a me-too proxy.

---

## 12. Minimum Viable Post-v1 Milestone

**Milestone: "Routing Decision Contract + Read-Only Decision API"**

Scope (documentation-first per Article 11):
1. **Spec section (post-v1 addendum) + ADR** defining: the RoutingDecision envelope
   (Section 5), constraint vocabulary (initial set: min_context_window, required_capabilities,
   allowed/denied provider or model identifiers, max normalized cost), typed status codes, freshness
   rule, and **resolution of the cost-semantics finding (Section 9)**.
2. **One adapter function** (e.g. `routing_decision(conn, task, profile, constraints, ...)`)
   composing `recommend` + `build_chain` + envelope assembly; read-only; provenance recording stays
   opt-in via the existing `record_recommendation`.
3. **CLI**: `route decide --task ... [--profile ...] [--json]` (human text default, JSON contract
   mode); read-only unless an explicit `--record` flag is passed.
4. **MCP tool** `routing_decision` returning the envelope (bounded tool-set addition, read-only).
5. Tests: determinism (same DB state ⇒ byte-identical JSON modulo created_at), constraint
   filtering, failure states, read-only enforcement, secret-scan hygiene of outputs.

Explicitly **not** in this milestone: any execution, proxying, scheduling, telemetry ingestion,
credential handling, score mutation, VS Code packaging work beyond an optional read-only command.

This milestone alone delivers the hypothesis' core value: task + constraints in → consumable,
explained, reproducible routing decision out — with zero constitutional friction.

---

## 13. Explicit Non-Goals (first post-v1 milestone)

* No request execution, proxying, retries, or streaming by AI-Hub (no Option B/C).
* No credential storage, brokering, or environment access (Article 6; §11 metadata-only stands).
* No daemon/scheduler/background refresh (D-P7 on-demand posture stands).
* No automatic score mutation from runtime telemetry (Section 8 governance).
* No prompt/completion/content logging ever.
* No modern-era MCP migration (D-1 stands); no new transports.
* No workspace/project discovery revival (ADR-0003/D-P5 deferral stands).
* No multi-tenant serving, authn/authz subsystem, or hosted service posture.
* No schema migration (envelope is computed; provenance tables suffice).
* No new Python dependencies (stdlib-only discipline stands).

---

## 14. Architectural Risks

| Risk | Assessment | Mitigation |
|---|---|---|
| Coupling AI-Hub to provider APIs | Avoided by staying metadata-level (only existing touchpoint: HEAD health checks) | Keep execution out (Non-Goals); any future adapter needs its own ADR |
| Credential handling | None introduced; config already rejects secret-like keys | Preserve §11; feedback design must reject secret-shaped fields (precedent: `_check_no_secrets`) |
| Nondeterministic routing | Low: ranking is pure over DB state; timestamps/UUID are identity-only (documented Art. 7 exception) | Contract echoes full policy; determinism tests mandated (Section 12.5) |
| Hidden state | Risk if consumers cache chains blindly | Explicit `computed_at` + documented freshness rule; recommend re-query per request (local reads are cheap) |
| Automatic score mutation | Real risk in feedback phase | Review-gated aggregation only; new event types via spec; never silent writes |
| Excessive gateway scope creep | The classic failure mode of this direction | Non-Goals section is binding; milestone boundary is the contract, not the proxy |
| Protocol coupling | Contained: bounded MCP subset; contract is transport-independent JSON | Envelope defined independently of MCP/CLI; versioned `contract_version` |
| Decision-layer latency | Low locally: SQLite reads; `recommend()` is O(models × dimensions) queries — fine at hundreds of models; the per-candidate re-query in `_eligible_models` and per-dimension lookups in `effective_score` are N+1 patterns that could matter at large catalogs | Acceptable for MVP; note as future optimization only (no premature caching layer, which would create hidden state) |
| Reproducibility problems | Aging (`age_days` uses wall-clock) and monitoring-derived scores make *cross-time* replay approximate; exact historical replay would need ADR-0004 snapshots (deferred) | Record full breakdown + policy in provenance/envelope (already largely done); document replay semantics honestly; revisit ADR-0004 only if owners need bit-exact replay |
| Governance/security regressions | New surfaces (CLI JSON, MCP tool) expand attack/error surface slightly | Follow established gates: query_only connections, read-only adapter rules, secret-scanning of anything ingested, EVENT_TYPES additions only via spec |

---

## 15. Constitutional Compliance Assessment

Against option A (decision-only API, the recommended position):

| Article | Compliance | Notes |
|---|---|---|
| 1 User Sovereignty | PASS | Nothing irreversible; execution stays with the user's application; provenance recording opt-in |
| 2 Recommendation Over Automation | PASS | AI-Hub recommends; the caller decides and acts. Option B/C would strain this — rejected |
| 3 Repository Independence | PASS | Contract is repo-agnostic; no workspace coupling; consumers integrate from any stack |
| 4 Explainability | PASS | Envelope carries rationale + per-dimension evidence + confidence (extends existing `build_explanation` output) |
| 5 Preservation of History | PASS | Append-only ledger untouched; no deletions; optional provenance reuse |
| 6 Security First | PASS | No credentials anywhere; metadata-only telemetry; secret-scanning precedents reused |
| 7 Deterministic Behaviour | PASS | Pure functions of DB state + explicit args; identity-only nondeterminism (UUID/timestamp), matching the documented exception |
| 8 Traceability | PASS | decision_version + contract_version + full policy echo; provenance IDs when recorded |
| 9 Extensibility | PASS | New constraint vocabularies/tools extend without redesign (profiles/preferences precedent) |
| 10 Truthfulness | PASS | Typed unknown/failure states; missing evidence surfaced, never fabricated |
| 11 Documentation Before Code | PASS | Milestone is spec+ADR first; this report is the spike input, not authorization |
| 12 Long-Term Maintainability | PASS | Versioned contract isolates consumers from internal evolution; avoids provider-API churn |

Options B and C fail the marked articles identified in Section 6 and are therefore not pursued.

---

## 16. Verdict

**CONDITIONAL GO** — viable, valuable, and architecturally compatible, **provided** the following
specific constraints are resolved by explicit owner-approved decisions in the governing spec before
implementation:

1. **Execution boundary pinned**: AI-Hub is decision-plane only (option A). Options B/C are
   formally rejected or deferred behind a future ADR (Sections 6, 13).
2. **Cost semantics defined once**: resolve the higher-is-better (weighted sum) vs lower-is-better
   (fallback sort) contradiction before cost influences routing (Section 9).
3. **Feedback governance decided**: runtime outcomes enter as review-gated evidence with new
   spec-defined event types; no automatic score mutation (Section 8). Not required for the first
   milestone, but its absence must be stated as a deliberate boundary.
4. **Freshness/consumption rule documented**: chains are point-in-time; consumers re-query or honor
   an explicit validity statement (Section 7).
5. **Write-path discipline**: `select_fallback`/`check_recovery` remain library-internal until a
   sanctioned, gated caller is specified; first-milestone consumption is read-only (Section 7.4).

All five conditions are ordinary, well-bounded design decisions inside the proposed first
milestone — none threatens viability. Every required building block already exists and was verified
in code.

## 17. Recommended Next Decision

Owner approval to open a post-v1 specification effort (documentation-first, per Article 11):

> **"Routing Decision Contract & Read-Only Decision API"** — a post-v1 spec addendum + ADR covering
> the RoutingDecision envelope (schema, constraints vocabulary, typed failure states, policy echo,
> freshness rule, cost-semantics resolution), followed by the minimal implementation: one read-only
> adapter function, one CLI command (`route decide`, JSON mode), one bounded MCP tool — with
> determinism, read-only enforcement, and failure-state tests.

If approved, the first concrete artifacts would be: `docs/review/POST-V1-ROUTING-DECISION-SPEC.md`
(or equivalent spec-section proposal) and an ADR recording the decision-plane boundary and the five
conditions above. **No implementation begins until that documentation is approved.**

---

*End of feasibility report. This document is uncommitted and unpushed; no other file was touched.*
