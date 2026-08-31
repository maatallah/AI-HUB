# POST-V1 ROUTING DECISION CONTRACT & READ-ONLY DECISION API — SPECIFICATION

Status: **IMPLEMENTED** (M1-M4 complete; `decision_version` 3.1.0 active; ADR accepted 2026-08-31)
Baseline: `515080495a34e106f46d90d151f451c2e94cfca0` ("Post-v1 adaptive routing feasibility baseline")
Feasibility basis: `docs/review/POST-V1-ADAPTIVE-AI-ROUTING-FEASIBILITY.md` (verdict CONDITIONAL GO)
Companion decision record: `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md`
Date: 2026-08-21
Revision: R1 (2026-08-21) — owner review: DECIDE made unconditionally read-only; provenance
recording separated into an explicit, independent RECORD DECISION operation (no `record` input)

Everything in this document that is not a citation of existing behavior is a **proposed**
contract. Nothing here authorizes or performs implementation. Per Constitution Article 11,
this specification precedes any code.

---

## 1. Purpose and Scope

This specification defines the smallest coherent post-v1 contract by which an external consumer
(application, IDE integration, MCP client, future execution layer) asks AI-Hub:

> "Given this task and these constraints, what AI should I use?"

and receives a deterministic, explainable, provenance-bearing **routing decision**.

The contract answers *what should be used*. It never performs *use it now*.
AI-Hub remains the intelligence/decision plane; the caller remains the execution/data plane.

Out of scope for this entire effort: request execution, proxying, retries, streaming, credential
handling, scheduling, telemetry ingestion, schema changes, new dependencies (see Section 14 and
the ADR non-goals).

---

## 2. Boundary Statement and Definitions

* **Decision plane (AI-Hub)**: computes routing decisions from persisted evidence using the
  existing Phase 3 engines (`recommendation.engine.recommend`, `fallback.engine.build_chain`),
  Phase 2 monitoring outputs (`providers.status`, `availability`, HEALTH_CHECK_* events), and the
  ADR-0001 normalized `scores` table. Unconditionally read-only: the decision operation performs
  zero writes (Section 11).
* **Execution plane (caller)**: sends prompts, calls providers, holds credentials, retries,
  streams, and observes outcomes. AI-Hub has no visibility into this plane under this contract.
* **Routing decision**: the envelope defined in Section 5 — a point-in-time, deterministic function
  of (persisted database state + request arguments).
* **Evidence**: stored scores (`scores`), monitoring state (`availability`, `providers.status`,
  health events), benchmark results. All append-only or derived; never rewritten.

---

## 3. Contract Inputs

Every input below is justified by an existing repository capability. No input is invented beyond
the three marked **[NEW]**, which are pure filters over existing engine inputs.

| # | Input | Type / values | Status | Justification (existing capability) |
|---|-------|---------------|--------|-------------------------------------|
| 1 | `task` | non-empty string | Existing | First argument of `recommendation.engine.recommend`; recorded in provenance (`recommendations.task`) |
| 2 | `profile` | built-in (`coding`, `reasoning`, `free`, `long_context`) or registered custom name; default = `recommendation.default_profile` config | Existing | `recommendation.profiles.get_profile` resolves and validates weights (sum = 1.0) |
| 3 | `min_context_window` | positive integer or null | Existing | Filter in `recommendation.engine._eligible_models` |
| 4 | `required_capabilities` | subset of `tool_calling`, `vision`, `streaming`, `json` | Existing | Mapped to `models.supports_*` columns in `_eligible_models` |
| 5 | `allowed_providers` / `denied_providers` | lists of provider ids or names | **[NEW]** | Pure post-filter over the same eligible set; registry identity already exists (`providers.id`, unique `name`). Needed so callers can express organizational/policy exclusions without editing the registry |
| 6 | `allowed_models` / `denied_models` | lists of model ids or identifiers | **[NEW]** | Same rationale at model granularity |
| 7 | `freshness.max_stale_days` | positive integer or absent | **[NEW]** | Eligibility filter on stored-evidence age; reuses the existing age computation (`scoring.engine.age_days`). Absent = no extra restriction (aging multipliers still apply). See Section 6 |
| 8 | `limit` | positive integer or absent | Existing | `recommend(..., limit=...)` truncation; envelope always records `total_eligible` so truncation is visible |

Rejected input ideas (not adopted): free-text budget/currency constraints (no cost semantics
tooling yet — see Section 7), region/data-residency constraints (no registry field supports them;
would require fabricated matching rules, violating Article 10), deadline/latency-class constraints
(latency is already a scored dimension and sort key; a separate constraint would duplicate it).

Deliberately absent from the input set: any persistence flag. The decision operation is
unconditionally read-only; a caller who wants a decision persisted invokes the separate
**RECORD DECISION** operation (Sections 9 and 11).

---

## 4. What the Decision Means

Given `(request inputs, database state D)`:

1. Resolve profile weights (`get_profile`).
2. Compute the eligible candidate set: provider status ∈ {ACTIVE, LIMITED, DEGRADED}
   (`ELIGIBLE_STATUSES`), context sufficiency, capability requirements — then apply caller
   filters (#5, #6) and the freshness filter (#7).
3. Score every remaining candidate per profile dimension via `scoring.engine.effective_score`
   (stored scores with aging; operational dimensions derived at read time).
4. Rank deterministically (v1.2 §7 Step 4 order; Section 5.1).
5. Build the fallback chain: primary + up to `max_chain_length` further eligible entries
   (`build_chain` semantics).
6. Emit the envelope (Section 5).

The decision is a **pure function** of its inputs. It activates nothing, contacts nothing, writes
nothing, emits no events, triggers no monitoring, and mutates nothing — under every input
combination, without exception (Section 11).

---

## 5. Output Envelope (PROPOSED)

Canonical JSON shape (illustrative; field names fixed by this spec, wire encoding chosen at
implementation):

```json
{
  "contract_version": "1",
  "status": "OK",
  "created_at": "<UTC timestamp of computation>",
  "request": {
    "task": "...", "profile": "...",
    "constraints": { "min_context_window": null, "required_capabilities": [],
                     "allowed_providers": [], "denied_providers": [],
                     "allowed_models": [], "denied_models": [] },
    "freshness": { "max_stale_days": null },
    "limit": null
  },
  "policy": {
    "decision_version": "3.1.0",
    "resolved_weights": { "<dimension>": <weight>, "..." : "..." },
    "aging_days": { "fresh": 30, "aging": 90, "old": 180 },
    "latency_threshold_ms": 10000,
    "derive_operational": true,
    "max_chain_length": 5
  },
  "total_eligible": 12,
  "candidates": [
    {
      "rank": 0,
      "provider_id": 3, "provider_name": "...", "provider_status": "ACTIVE",
      "model_id": 7, "model_identifier": "...",
      "final_score": 78.42, "confidence": 0.81,
      "breakdown": {
        "<dimension>": { "value": 85.0, "weight": 0.4, "contribution": 34.0,
                          "confidence": 0.9, "source": "BENCHMARK", "aged": 1.0 }
      },
      "flags": ["insufficient data: cost"]
    }
  ],
  "selected": { "rank": 0 },
  "fallback_chain": [ { "rank": 1 }, { "rank": 2 } ],
  "rationale": "<primary explanation text; chain summary>",
  "provenance": { "decision_id": null, "recorded": false },
  "warnings": []
}
```

### 5.1 Field justification

For every field: why it is needed, which existing capability supports it, and its epistemic class
(**authoritative** = persisted fact; **derived** = computed by this contract from authoritative
data; **informational** = echo/context).

| Field | Why needed | Supporting capability | Class |
|---|---|---|---|
| `contract_version` | Consumers must know the wire-format they parsed; enables additive evolution (Section 15) | New marker; pattern follows `decision_version` governance | Informational |
| `status` | Callers must distinguish a real recommendation from an evidence failure (Article 10); prevents silent garbage consumption | New; composed from existing eligibility/evidence checks | Derived |
| `created_at` | Point-in-time anchor; chains/scores age | Timestamps exist throughout (`events.occurred_at`, `recommendations.requested_at`) | Informational |
| `request.*` | Exact echo so the envelope is self-describing and auditable; reproducibility requires knowing the question | Provenance already stores task/profile; constraints echo is new | Informational |
| `policy.decision_version` | Reproducibility across logic versions (v1.2 §8) | `config.recommendation.decision_version` (default `3.1.0`), already stored in provenance | Authoritative (config) |
| `policy.resolved_weights` | Ranking is meaningless without the weights actually applied; custom profiles are DB state | `recommendation.profiles.get_profile`; weights already embedded per-dimension in `score_breakdown` | Authoritative (resolved) |
| `policy.aging_days`, `latency_threshold_ms`, `derive_operational`, `max_chain_length` | These parameters change results; echoing them makes the envelope reproducible without config access | `app.config.DEFAULT_CONFIG` validated fields | Authoritative (config) |
| `total_eligible` | Distinguishes "truncated by limit" from "few candidates exist" | Computable from the eligible set pre-limit | Derived |
| `candidates[].rank` | Stable reference for `selected`/`fallback_chain` | Ordering already deterministic (`_sort_key`) | Derived |
| `candidates[].provider_*/model_*` | Identity of what to use | `providers`, `models` tables; already in `Recommendation` | Authoritative |
| `candidates[].final_score`, `confidence` | The ranking result and its trust level | `Recommendation.final_score/confidence` (weighted mean of dimension confidences) | Derived |
| `candidates[].breakdown` | Article 4 evidence: which dimension contributed what, from which source, aged how | `Recommendation.breakdown` (already persisted in provenance as `score_breakdown`) | Derived (from authoritative scores) |
| `candidates[].flags` | Truthful gaps: degraded provider, insufficient data (Article 10) | `Recommendation.flags` produced by the engine today | Derived |
| `selected` | The direct answer to "what should I use" | `Chain.primary` | Derived |
| `fallback_chain[]` | Ordered alternatives if the primary fails at execution time | `Chain.fallbacks` via `build_chain` | Derived |
| `rationale` | Human-readable what/why/evidence/confidence (Article 4) | `recommendation.explain.build_explanation` | Derived |
| `provenance.decision_id`, `provenance.recorded` | Truthful persistence state: `recorded=false` with `decision_id=null` marks the envelope ephemeral/unrecorded; a non-null id hooks the envelope to the append-only ledger only if the separate RECORD DECISION operation stored it | `record_recommendation` UUID; `RECOMMENDATION_CREATED` event (invoked solely by RECORD, never by DECIDE) | Authoritative (when recorded); informational otherwise |
| `warnings[]` | Envelope-level aggregation of cross-candidate conditions (Section 10) | Composition of existing flag text | Derived |

Fields deliberately **not** included: token pricing in currency (no such evidence exists yet),
region/residency, retry policies, prompt templates, TTL/expiry (freshness is expressed via
`created_at` + aging multipliers + the documented rule, not a server-imposed expiry — Section 6),
any execution hint beyond the ordered chain.

### 5.2 Candidate ordering (normative)

Exactly the existing v1.2 §7 Step 4 order implemented by `recommendation.engine._sort_key`:
final score desc → availability desc → reliability desc → cost asc → latency asc →
`model_identifier` asc. Missing dimensions sort last within each key (sentinels `-1.0` for
descending keys, `1e9` for ascending keys today). **One normative change is specified by
Section 7** (cost direction) and takes effect only when implemented under separate authorization;
until then the shipped order stands and the envelope's `policy` block makes any version difference
auditable.

---

## 6. Freshness Rule (resolves feasibility constraint 4)

Existing mechanisms reused verbatim — no new clock, no new store:

* **Stored scores** carry `scored_at`; `scoring.engine.age_multiplier` decays confidence:
  ≤30 days ×1.00, ≤90 ×0.90, ≤180 ×0.75, >180 ×0.50 (boundaries configurable, echoed in
  `policy.aging_days`).
* **Derived operational dimensions** (availability, reliability, latency, context_window) are
  computed at read time from current monitoring rows/events (`scoring.derive`); their freshness is
  the freshness of the last monitoring run. The contract **never triggers monitoring** (on-demand
  posture, Phase 6 D-P7): if monitoring has never run, derived dimensions are absent and surface as
  insufficient-data flags — truthful unknowns, not zeros.

Normative rules:

1. **Stale data may be used.** It is never silently discarded (Articles 5, 10); it participates
   with decayed confidence, visibly (`breakdown[].aged`, `flags`).
2. **Caller freshness requirement.** `freshness.max_stale_days` (optional) excludes candidates
   whose newest stored evidence relevant to the profile's weighted dimensions is older than the
   bound. Candidates excluded solely by this filter are reported in `warnings`
   (`"excluded by freshness: N"`). If the eligible set becomes empty because of it, status is
   `CONSTRAINT_UNSATISFIABLE` with that detail.
3. **Output expression.** `created_at` anchors evaluation time; per-dimension `aged` multipliers
   and `scored_at`-backed sources in `breakdown` expose evidence ages; no artificial TTL/expiry
   field is defined. A chain older than the caller's tolerance is handled by re-querying — local
   SQLite reads make re-query per request the recommended default (feasibility §7.2).

---

## 7. Cost Semantics (resolves feasibility constraint 2)

**Canonical definition (PROPOSED):** the `cost` dimension is a normalized **affordability score on
the existing 0–100 scale where higher = more favorable cost (cheaper)**. This makes cost consistent
with every other dimension: same validation (`scoring.ingest._validate_value`), same weighted-sum
formula (`final += weight × value`), same "higher is better" reading.

This resolves the inconsistency identified in the feasibility study (§9): the fallback tie-break
in `_sort_key` currently sorts raw `cost` **ascending** (price-like), contradicting the weighted
formula's higher-is-better treatment. **When this contract is implemented, `_sort_key` must treat
canonical cost like every other quality dimension (descending).** That is a one-line normative
change recorded here; it is *not* applied in this documentation effort, and until applied, the
shipped behavior stands (profiles weighting cost 0.00, e.g. `coding`, are unaffected either way).

Evidence classes — strictly distinguished:

| Class | Meaning | Source vocabulary (existing) | Participation rule |
|---|---|---|---|
| **Known pricing** | Declared list prices (per-token/unit) entered manually or imported like benchmarks | `MANUAL`, `OFFICIAL_INFORMATION`, `BENCHMARK` | Converted to the canonical score by a documented normalization formula (pattern: `benchmark.ingest.FORMULAS` mapping discipline). Authoritative-as-declared |
| **Estimated cost** | Interpolated/class-based approximation | `MANUAL` with explicit estimation note, or `USER_FEEDBACK` | Participates with reduced/declared confidence; MUST be flagged as estimated wherever displayed (Article 10) |
| **Observed usage** | Self-reported token counts/spend from the executing application | `USER_FEEDBACK`, `AUTOMATED_TEST` | Future feedback-loop evidence only (Section 12); never auto-applied |
| **Actual provider billing** | Real invoices/metered billing | — | **Out of scope permanently for this contract**: requires credential custody (Article 6; spec §11 metadata-only) |
| **Unknown cost** | No evidence | NULL | Contributes 0 to the weighted sum and raises an `insufficient data: cost` flag (existing engine behavior). **Never silently treated as zero-cost**; in ordering, missing cost sorts last |

No credential storage is introduced or implied. Populating cost scores continues to use the
existing generic paths (`score set --dimension cost`, benchmark import with a cost mapping);
dedicated tooling is deferred (Section 14).

---

## 8. Fallback Contract

Exposes the existing deterministic capability (`fallback.engine.build_chain`) as **data**:

* `selected` = chain primary (rank 0). Each `fallback_chain[]` entry references the next ranked
  eligible candidate; ordering is the candidate ordering (§5.2). Entries carry their flags — a
  DEGRADED provider appears only as a flagged last resort (`LAST_RESORT_STATUSES` semantics).
* **Why a fallback exists** is implicit and auditable: chain membership = deterministic ranking ∩
  build-time eligibility. There is no hidden preference logic.
* Chain length may be shorter than `policy.max_chain_length` (few eligible candidates); length 0
  with no primary yields `NO_CANDIDATE`.
* **Caller permissions**: attempt entries in order; advance on execution-plane failure; re-query
  for a fresh chain at any time (recommended per request). The caller owns trigger definitions
  (what counts as "failed") — AI-Hub's signal vocabulary (`QUOTA_STATUS_CODES`,
  `classify_status_code`) is available as guidance, not enforced here.
* **AI-Hub does not execute fallbacks.** `select_fallback` / `check_recovery` remain
  library-internal functions with no external exposure in this contract (write-path discipline,
  Section 11): consuming the chain never writes `FALLBACK_TRIGGERED` / `FALLBACK_RECOVERED`
  events. Those events continue to belong to future, explicitly governed runtime flows.

---

## 9. Explanation and Provenance

Two strictly separated operations, per the owner-mandated invariant **"decide never writes"** —
all reusing existing concepts, creating **no second source of truth**:

* **DECIDE** (this contract): reads persisted state, computes, returns the envelope. Zero writes,
  zero events, zero monitoring — under every input combination. Every envelope it produces is
  ephemeral/unrecorded: `provenance.recorded = false`, `provenance.decision_id = null`.
* **RECORD DECISION** (a separate conceptual operation, specified here; implemented only under
  future authorization): explicit, caller-initiated append-only persistence of a previously
  produced decision. It reuses the existing `recommendation.provenance.record_recommendation`
  mechanism verbatim — one `recommendations` row per ranked candidate (UUID id, task, profile,
  ids, `decision_version`, `score_breakdown`, explanation, confidence) plus
  `RECOMMENDATION_CREATED` events — exactly the CLI `recommend top` behavior today. Conceptual
  relationship: RECORD consumes a decision (its envelope/candidate data) as input and yields the
  persisted identity; DECIDE neither knows nor cares whether RECORD ever runs. On a recorded
  decision, `provenance.decision_id` carries the primary row's UUID; companion rows are
  discoverable via `list_recommendations` (same task/profile/timestamp neighborhood).

In-envelope reproduction information (always present, independent of any recording): `policy`
block (decision version, resolved weights, aging parameters, thresholds, chain length), `request`
echo, per-candidate `breakdown` (value/weight/contribution/confidence/source/aged), `created_at`.
With these, any reader can recompute the ranking from the cited evidence.

Until RECORD is invoked, auditability depends on the caller's retention of the envelope. This is
stated deliberately: an unconditionally read-only DECIDE (owner sovereignty) provides ledger
coverage only where a caller explicitly requests persistence through the separate operation —
consistent with how MCP `recommend_top` already behaves versus the recording CLI.

---

## 10. Error and Unknown Semantics

Normative statuses and error behavior. The contract must never present a recommendation that the
evidence does not support (Article 10).

| Condition | Behavior |
|---|---|
| Invalid profile name | Typed input error (existing `ProfileError`); **no envelope** |
| Empty/invalid task | Typed input error; no envelope |
| No eligible candidates (registry/eligibility filters) | `status = NO_CANDIDATE`; `warnings` states which eligibility rules emptied the set; `candidates: []` |
| Candidates existed before caller constraints, none after (allow/deny/freshness) | `status = CONSTRAINT_UNSATISFIABLE`; `warnings` names the excluding constraint(s) and counts |
| ≥1 candidate but **no** candidate has evidence for **any** profile-weighted dimension | `status = INSUFFICIENT_DATA`; candidates still returned (zero-filled contributions, flagged) so the caller sees the landscape truthfully |
| Partial evidence (some dimensions missing on some candidates) | `status = OK`; gaps appear per-candidate in `flags` and depress `confidence` (existing engine behavior) |
| All candidates stale relative to `freshness.max_stale_days` | `CONSTRAINT_UNSATISFIABLE` (filter) — or, without the filter, `OK` with heavily aged multipliers visible (decay is the honest signal) |
| Monitoring unavailable / never run | Derived operational dimensions absent → insufficient-data flags; lifecycle statuses still apply; never fabricated |
| Contradictory evidence | **Not detected today** (no such engine capability). Out of scope; conflicting sources remain visible via `breakdown[].source`. Listed as deferred (Section 14) rather than invented |
| Unknown cost | NULL + flag; never zero (Section 7) |
| Provider/model unavailable at execution time | Undetectable by the decision plane; eligibility reflects persisted state only. Runtime failure handling belongs to the caller (Section 8) |

---

## 11. Write-Path Discipline (resolves feasibility constraint 5)

The DECIDE operation is **unconditionally read-only**: zero writes, zero events, zero monitoring,
zero mutation. There is no input, flag, or database condition under which it writes — the
invariant **"decide never writes"** is mechanical, enforced by the absence of any write path in
the operation rather than by convention.

Persistence exists only as the separate **RECORD DECISION** operation (Section 9): the single
sanctioned, explicitly invoked, append-only write of the post-v1 design. It reuses the existing
`record_recommendation` path (`recommendations` rows + `RECOMMENDATION_CREATED` events) —
non-destructive, already exercised by the released CLI — preserving traceability (Article 8)
without expanding any write surface. DECIDE is fully functional and fully compliant if RECORD is
never implemented or never called.

The DECIDE operation:

**May read:** `providers`, `models`, `scores`, `availability`, `events` (via existing history
views), `preferences` (custom profiles), effective configuration.

**May calculate:** eligibility, effective/derived scores, ranking, chain, explanations, the
envelope itself. All computations are the existing engines'; the API adds no decision logic.

**May return:** the envelope (plain JSON-serializable structures — the `connectors.adapter`
convention).

**Must never mutate:**

* provider lifecycle / activation (`apply_lifecycle`, `archive_provider` untouched)
* registry state (`add/update_provider`, `add/update_model` untouched)
* discovery candidates (`approve/reject_candidate` untouched)
* benchmark runs/results (`benchmark.ingest` untouched)
* historical events (no updates/deletes; no new event types)
* governance configuration (no config writes; no secret-shaped keys accepted —
  `config._reject_secrets` precedent)
* credentials (never stored, never requested)

Explicitly **not exposed by DECIDE**: `select_fallback`, `check_recovery`, `update_availability`,
`apply_lifecycle`, `record_quota_signal`, `set_score`. `record_recommendation` is reachable only
through the separate RECORD DECISION operation. These remain internal or CLI-governed
capabilities.

---

## 12. Feedback Governance Boundary (resolves feasibility constraint 3)

Conceptual layers, strictly ordered:

1. **Routing decision** (this contract) — pure read-only computation; never self-records (persistence only via the separate RECORD DECISION operation, Sections 9/11).
2. **Execution telemetry** — lives in the execution plane. AI-Hub does not collect it under this
   contract. Any future ingestion requires new spec-defined event types (`core.events.EVENT_TYPES`
   is a closed set) and metadata-only payloads (no prompts, no content, no credentials).
3. **Evidence** — benchmark evidence enters only via the governed importer (hashes, mappings,
   source=BENCHMARK); runtime observations, if ever added, must follow the same gate.
4. **Authoritative registry data** — providers/models/scores mutate only through existing governed
   operations performed by authorized actors.
5. **Derived metrics** — history/trend views are computed, never stored or mutated.

Accordingly, observed runtime feedback may:

* **inform future decisions** — YES, but only after passing a human-reviewed aggregation step that
  produces explicitly sourced score updates (e.g., `USER_FEEDBACK`), mirroring the benchmark-import
  and discovery-approval disciplines;
* **modify derived metrics** — NO (derived metrics are computations);
* **modify authoritative scores automatically** — **NO.** Automatic mutation is not authorized:
  Article 10 (observations ≠ verified quality), Article 7 (decisions must not depend on unreviewed
  runtime noise), and project precedent (automated discovery stops at PENDING_REVIEW; automated
  benchmarks enter through hashed, mapped import);
* **trigger review** — YES, conceptually: accumulated outcomes may queue a human review; approval
  remains human (Articles 1, 2).

This section fixes the boundary only; it authorizes no telemetry mechanism.

---

## 13. External Consumers (assessment only — none implemented here)

| Consumer | Conceptual fit |
|---|---|
| CLI | Natural first surface: e.g. a `route decide` command rendering text by default, envelope as JSON with a flag. Mirrors existing command style (`app.main`) |
| Future HTTP/API caller | The envelope is transport-independent JSON; a thin stdio/HTTP wrapper could serve it. No server exists today; adding one would be a separately governed decision |
| MCP | Fits the bounded tools-only pattern (`connectors.mcp.tools`): one additional read-only tool returning the envelope; server stays `PRAGMA query_only`, legacy-era stdio (D-1 unchanged) |
| VS Code | Presentation-over-CLI pattern (`features.ts`): one more read-only command rendering the decision; no decision logic in the extension |
| Another application | Consumes the envelope directly (library/CLI); needs only JSON parsing and the documented ordering/status rules |
| Future gateway/router | The intended long-term split: gateway executes and may report outcomes back through the (future, governed) feedback boundary of Section 12 |

All consumers receive identical bytes for identical inputs — the contract, not the transport,
defines the decision.

---

## 14. Execution-Plane Boundary

The contract may return: "Use Model A; fallback B → C," with full rationale and evidence.

It must NOT itself: send prompts; call provider APIs; handle provider credentials; stream
responses; retry provider calls; proxy requests; transform model responses; measure execution-plane
latency (its latency evidence comes only from its own metadata health checks).

This is the feasibility study's Option A. Options B (execution adapter) and C (gateway) are
rejected/deferred in the ADR.

---

## 15. Versioning

Simplest viable scheme — two version fields, no negotiation protocol:

* **`contract_version`** (envelope): starts at `"1"`. Evolution rule: within v1, changes are
  additive-only (new OPTIONAL fields; new status values forbidden — adding one is a breaking
  change requiring v2). Consumers MUST ignore unrecognized fields.
* **`policy.decision_version`** (existing): continues to govern decision *logic* versions
  (`config.recommendation.decision_version`, already persisted in provenance rows).
* **`decision_id`**: the existing UUID provenance identity; identifies the record, never affects
  content (documented Article 7 exception).
* **Backward compatibility**: old envelopes remain interpretable (self-describing policy block);
  old provenance rows remain queryable (append-only ledger, Article 8). The §7 cost-direction
  change is the kind of change that bumps `decision_version` and is visible in every envelope
  issued after adoption.

---

## 16. Security and Privacy

* **No API keys or credentials**: the contract reads none, accepts none, returns none. Config-level
  rejection of secret-shaped keys remains active (`app.config._reject_secrets`).
* **No prompt retention**: the contract never sees prompts. `task` is a short classification label
  (existing usage, e.g. `"python web service"`), not user content. Because `request.task` is
  echoed verbatim, callers SHOULD pass category labels, never sensitive text. (An opaque
  `task_ref` alternative was considered and rejected as over-design; the echo rule suffices.)
* **No sensitive user data**: outputs contain registry metadata, scores, and text explanations
  only.
* **Non-destructive operation**: DECIDE performs zero writes — always; the only persistence path
  is the separate, explicitly invoked append-only RECORD DECISION operation (Section 11).

---

## 17. Minimum Viable Contract

**REQUIRED FOR V1 OF THE CONTRACT**

1. Envelope: `contract_version`, `status` (4 values, §10), `created_at`, `request` echo,
   `policy` block, `total_eligible`, `candidates[]` (identity, final_score, confidence,
   breakdown, flags, rank), `selected`, `fallback_chain[]`, `rationale`, `provenance`
   (reporting ephemeral/unrecorded state until RECORD runs), `warnings[]`.
2. Inputs: task, profile, min_context_window, required_capabilities, allow/deny provider/model
   lists, `freshness.max_stale_days`, limit. **No persistence input exists** — DECIDE cannot
   write by construction.
3. Determinism rules (§5.2, Section 5 context), freshness rule (§6), cost semantics **definition**
   (§7) including the normative sort-direction fix to apply at implementation time.
4. Error/unknown semantics (§10) and write-path discipline (§11).
5. One read-only exposure to start (CLI recommended); adapter/MCP wiring may follow in the same
   milestone or the next.
6. The separate **RECORD DECISION** operation — classified **REQUIRED**, not deferred: Article 8
   traceability and the existing provenance requirements (append-only ledger, persisted
   `decision_version`) require a sanctioned persistence route, and the mechanism already exists
   (`record_recommendation`; zero new write surface). It is a distinct operation from DECIDE,
   never a parameter of it, and may be delivered in the same milestone or immediately after —
   but the post-v1 effort is incomplete without it.

**DEFERRED / OPTIONAL**

* `max_cost` constraint knob (semantics defined; enforcement later)
* Dedicated cost-normalization tooling (generic `score set` / benchmark mapping suffice initially)
* Runtime feedback events and review queueing (Section 12 boundary only)
* HTTP/server surface; MCP tool; VS Code command (consumer wiring)
* ADR-0004 point-in-time snapshots for bit-exact cross-time replay
* Contradictory-evidence detection
* Region/data-residency and deadline constraints
* Per-model availability overrides (monitoring is provider-scoped today)

---

## 18. Constitutional Compliance

| Principle | Compliance | Tension | Resolution |
|---|---|---|---|
| Art. 1 User Sovereignty | DECIDE is unconditionally zero-write; execution stays with the caller | None for DECIDE; RECORD writes only when explicitly invoked | The read-only decision operation requires no write consent because it performs no write; persistence requires an explicit RECORD DECISION operation |
| Art. 2 Recommendation Over Automation | Returns advice; performs nothing | Machine-consumable chain could feed fully automated execution | The contract returns data only; consent for execution is the caller's governance problem, outside AI-Hub's write surface |
| Art. 3 Repository Independence | Task/profile/constraints in; envelope out; no repo coupling | — | None |
| Art. 4 Explainability | Rationale + breakdown + confidence mandatory in every OK envelope | — | None |
| Art. 5 Preservation of History | Append-only ledger untouched; provenance reuses existing rows | — | None |
| Art. 6 Security First | No credentials anywhere; cost via declared/reported data only | — | None |
| Art. 7 Deterministic Behaviour | Pure function of DB state + args; full policy echo; explicit tie-breaks | Wall-clock aging varies with evaluation time | Documented as input-time dependence (same-instant determinism guaranteed); cross-time bit-exact replay honestly not promised (ADR-0004 future) |
| Art. 8 Traceability | decision_version + contract_version + policy echo + RECORD-provided ledger IDs | Unrecorded decisions leave no ledger trace | Documented property of an unconditionally read-only DECIDE; callers needing audit invoke the explicit RECORD DECISION operation |
| Art. 9 Extensibility | Additive versioning; constraint vocabulary extensible without redesign | — | None |
| Art. 10 Truthfulness | Four statuses; flags; NULL cost never zero; estimates labeled | — | None |
| Art. 11 Documentation Before Code | This document; no implementation performed | — | None |
| Art. 12 Long-Term Maintainability | Transport-independent envelope; bounded surfaces; no new dependencies | — | None |

---

## 19. Relationship to Prior Baselines

* Extends, without altering, the released v1 architecture: Phase 3 engines supply every
  computation; Phase 5 supplies the read-only exposure pattern; Phase 6 supplies the
  governance-gate precedents cited in Sections 7 and 12.
* Implements the design mandate of `docs/review/POST-V1-ADAPTIVE-AI-ROUTING-FEASIBILITY.md`
  (commit `5150804`), resolving its five conditions in Sections 5–12.
* Not a Phase: v1 roadmap (v1.2 §15) is complete and closed; this is a post-v1 contract governed by
  its own spec + ADR.

---

*End of specification. Proposed only — no code, schema, configuration, test, MCP, or VS Code
artifact was created or modified for this contract.*
