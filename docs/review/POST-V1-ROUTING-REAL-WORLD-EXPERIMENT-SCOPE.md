# POST-V1 ROUTING — REAL-WORLD EXPERIMENT SCOPE

Status: **PLANNING DOCUMENT** (scope definition only — no implementation performed or authorized)
Baseline: M4 closure `1a465f384071f5eca361463fd97037b93a3998b1` (`decision_version` 3.1.0 active;
548/548 tests passing)
Date: 2026-09-01
Nature: Owner-authorized experiment scope for evaluating the existing M1–M4 routing decision
plane under a small set of real OpenCode tasks. **Not** an implementation milestone. **Not** M5.
**Not** adaptive learning. **Not** a feedback-ingestion mechanism. **Not** an authorization to
modify AI-Hub.

Governing documents:

* `CONSTITUTION.md` — permanent principles (Arts. 1–12)
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — normative contract; §12 feedback
  governance boundary; §14 execution-plane boundary
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` — approved decision record; Option A
  decision-plane-only boundary is binding
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md` through `M4-CLOSURE.md` — completed
  milestone authorities; M1–M4 closed
* `START-HERE.md` — current project status: "no M5 authorized"
* `handover/CURRENT-STATE.md` — current state: "no M5 authorized"

---

## 1. Purpose

Evaluate the behavior and usefulness of the existing M1–M4 routing decision plane under a small
set of real OpenCode tasks. The experiment answers one question:

> **Does the M4 routing decision plane produce useful, actionable recommendations for real
> development tasks?**

The experiment is conducted entirely through the existing `route decide` and `route record` CLI
operations. No AI-Hub source code, configuration, schema, database structure, provider/model
registry data, routing algorithm, scoring semantics, or connector behavior is modified,
authorized to be modified, or implied to require modification by this scope.

---

## 2. What This Experiment Is

| Property | Classification |
|---|---|
| Nature | Owner-executed evaluation of existing M4 behavior |
| Scope | Exactly 8 predefined tasks (Section 3) |
| Mechanism | Existing `route decide` + `route record` CLI operations |
| Observer | Human; observations recorded externally/manual ledger |
| Duration | Until Task 8 is complete and observations recorded |
| Relationship to AI-Hub | Read-only consumer of existing routing decisions |

---

## 3. What This Experiment Is NOT

| Property | Classification |
|---|---|
| Implementation milestone | **NO** — no code, tests, or artifacts are produced for AI-Hub |
| M5 | **NO** — M5 is explicitly not authorized (`START-HERE.md`, `handover/CURRENT-STATE.md`) |
| Adaptive learning | **NO** — no feedback loop is implemented or authorized |
| Feedback-ingestion mechanism | **NO** — no `USER_FEEDBACK` source is created; no score mutation occurs |
| Telemetry collection | **NO** — execution telemetry remains in the execution plane (contract §12) |
| Routing algorithm change | **NO** — the existing `_sort_key` and scoring behavior are used as-is |
| Scoring semantics change | **NO** — no dimension weights, formulas, or aging parameters are altered |
| Provider/model registry change | **NO** — no providers or models are added, updated, or archived |
| Configuration change | **NO** — `config.toml` and `app/config.py` are untouched |
| Schema change | **NO** — `database/schema.sql` and runtime schema are untouched |
| Decision contract change | **NO** — `contract_version` remains `"1"`; envelope format is unchanged |
| Connector change | **NO** — MCP, VS Code, and adapter behavior are untouched |
| New routing capability | **NO** — only existing CLI operations are used |
| Authorization for future work | **NO** — findings require separate owner-approved scope |

---

## 4. Fixed Task Set

The experiment consists of exactly these 8 tasks. No task may be added, removed, replaced, or
extended.

| # | Task Description | Profile | Constraints | Notes |
|---|---|---|---|---|
| 1 | Write a Python function that reads a CSV file and returns a list of dictionaries. | `coding` | (none) | Basic coding task |
| 2 | Explain the difference between TCP and UDP, including when to use each. | `reasoning` | (none) | Reasoning task |
| 3 | Generate a short email greeting for a meeting reminder. | `free` | (none) | Unconstrained task |
| 4 | Summarize the contents of this repository's `CONSTITUTION.md` file. | `long_context` | (none) | Long-context task |
| 5 | Describe what you see in a supplied screenshot. | `coding` | `required_capabilities: [vision]` | Capability constraint |
| 6 | Write a Python one-liner that filters even numbers from a list. | `coding` | (none) | Simple coding task |
| 7 | Process a 500KB text file and extract all unique words. | `coding` | `min_context_window: 500000` | Context-window constraint |
| 8 | Refactor a specific function from the codebase to use async/await. | `coding` | (none) | Codebase-specific task |

### 4.1 Task Invariants

* The task list is **closed**. No new tasks may be introduced during experiment execution.
* Each task is executed **sequentially** (Task 1 through Task 8 in order).
* Each task uses the **existing** `route decide` CLI operation with the declared profile and
  constraints.
* The `--json` flag is used to capture the full decision envelope for each task.
* Where appropriate, `route record` is invoked to persist the decision envelope.
* The recommended model/provider is used in OpenCode to perform the actual task.
* The human observer records the outcome in an external manual ledger (Section 7).

---

## 5. Execution Model

### 5.1 Per-Task Sequence

```
1. Invoke: python -m app.main route decide --task "<task>" --profile <profile> [--json]
           [--capability <cap>] [--min-context <window>]
2. Inspect: the resulting decision envelope (status, selected, fallback_chain, rationale, flags)
3. Record:  python -m app.main route record < envelope.json   (where appropriate)
4. Execute: use the recommended model/provider in OpenCode to perform the task
5. Observe: the actual execution result (quality, latency, errors, usefulness)
6. Log:     record the observation in the external manual ledger (Section 7)
7. Proceed: move to the next task
```

### 5.2 Distinction of Planes

The experiment must clearly distinguish between:

| Plane | What Happens | Where |
|---|---|---|
| **Routing decision** | `route decide` produces an envelope | AI-Hub (read-only) |
| **Persistence** | `route record` appends to provenance ledger | AI-Hub (append-only) |
| **Execution** | OpenCode uses the recommended model/provider | OpenCode (execution plane) |
| **Observation** | Human records the outcome | External manual ledger |
| **AI-Hub state** | Unchanged by the experiment | database/ai_hub.db |

---

## 6. Hard Scope Boundary

### 6.1 Invariant

> **An experimental observation is not automatically AI-Hub evidence, a score, feedback, or
> learning.**

### 6.2 Finding Rule

> **Any proposed implementation, policy change, data change, architectural change, additional
> experiment, or extension discovered during this experiment is a FINDING ONLY and requires a
> separate owner-approved scope before any implementation or scope expansion.**

### 6.3 Prohibited Actions

This experiment does NOT authorize:

* M5 implementation
* adaptive-learning implementation
* automatic score mutation
* `USER_FEEDBACK` ingestion into AI-Hub
* telemetry collection into AI-Hub
* changes to routing algorithms (`recommendation/engine.py`, `_sort_key`)
* changes to scoring semantics (`scoring/engine.py`, `scoring/derive.py`, `scoring/ingest.py`)
* changes to provider/model registry data (`core/providers.py`, `core/models.py`)
* adding providers or models
* changes to configuration (`config.toml`, `app/config.py`, `templates/config.toml`)
* changes to the database schema (`database/schema.sql`)
* changes to the routing decision contract (`docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md`)
* changes to the MCP connector (`connectors/mcp/`)
* changes to the VS Code/OpenCode integration (`connectors/vscode/`)
* new routing capabilities beyond existing `route decide` / `route record`
* additional experiment tasks beyond the 8 defined in Section 4
* automatic promotion of observations into AI-Hub scores or evidence

### 6.4 Immediate Stop Conditions

The experiment MUST pause immediately if completing a task would require:

* modifying AI-Hub source code
* changing routing behavior
* changing configuration
* changing schema
* changing provider/model data
* changing the decision contract
* implementing feedback
* implementing telemetry
* expanding the task set
* or otherwise exceeding this scope

Any such situation must be recorded as a **finding** in the closure report (Section 9) rather than
solved inside the experiment.

---

## 7. Observation Model

### 7.1 Purpose

The observation model captures, for each task, what the routing decision recommended and how the
actual execution performed. It is a **manual, external** record — not an AI-Hub feedback pipeline.

### 7.2 Per-Task Observation Record

For each of the 8 tasks, the observer records at minimum:

| Field | Description |
|---|---|
| **Task #** | Task number (1–8) |
| **Profile** | Routing profile used (coding / reasoning / free / long_context) |
| **Constraints** | Any constraints applied (capability, min_context_window, allow/deny lists) |
| **Decision Version** | From envelope `policy.decision_version` |
| **Status** | Envelope status (OK / NO_CANDIDATE / CONSTRAINT_UNSATISFIABLE / INSUFFICIENT_DATA) |
| **Selected Provider** | From envelope `selected` → provider identity |
| **Selected Model** | From envelope `selected` → model identifier |
| **Fallback Chain** | From envelope `fallback_chain` (if any) |
| **Total Eligible** | From envelope `total_eligible` |
| **Rationale** | From envelope `rationale` (or summary) |
| **Flags** | From envelope `warnings` or candidate `flags` |
| **Execution Attempted** | Yes / No — whether the task was actually attempted in OpenCode |
| **Execution Completed** | Yes / No / Partial — whether the task was completed |
| **Quality Assessment** | Qualitative rating of the execution result (e.g., good / adequate / poor / failed) |
| **Usefulness Assessment** | Whether the recommended model was appropriate for the task (yes / no / partially) |
| **Notable Problems** | Any mismatches, errors, or unexpected behavior observed |
| **Routing Observation** | Any noteworthy observation about the routing decision itself |

### 7.3 Observation Scope

The observation record is **experimental material**, not an AI-Hub feedback pipeline.

* Observations are recorded **externally** (spreadsheet, text file, or similar).
* Observations are **never** ingested into AI-Hub.
* Observations are **never** converted into scores, events, or evidence.
* Observations may be **analyzed by humans** to inform future decisions about AI-Hub development.
* Any future conversion of observations into AI-Hub evidence or score updates would require a
  **separate governed process and authorization** (contract §12).

---

## 8. No Automatic Learning

### 8.1 Terminology

The following terms are precise and must not be used interchangeably:

| Term | Meaning in This Experiment |
|---|---|
| **Routing decision** | The envelope produced by `route decide` from current stored state |
| **Execution result** | The outcome of using the recommended model in OpenCode |
| **Observation** | The human-recorded comparison of routing decision vs. execution result |
| **Finding** | A conclusion drawn from observations; requires separate scope for any action |
| **Evidence** | Authoritative data in AI-Hub's database (scores, events, provider state) |
| **Score** | A numeric value in the `scores` table with a source attribution |
| **Learning** | NOT APPLICABLE — this experiment does not implement learning |

### 8.2 Prohibition

This experiment does NOT produce:

* AI-Hub evidence
* AI-Hub scores
* AI-Hub events
* AI-Hub feedback
* automatic routing improvements
* adaptive model selection
* learning signals

The experiment produces **observations** and **findings**. That is all.

---

## 9. Closure

### 9.1 Trigger

The experiment ends after Task 8 has been executed and its observation recorded.

### 9.2 Required Closure Artifact

After Task 8, a closure report is prepared summarizing:

1. **Execution summary** — which tasks were executed, which were skipped (if any, with reasons)
2. **Routing decisions** — summary of envelopes received (statuses, selected models, fallbacks)
3. **Observations** — consolidated observation records for all 8 tasks
4. **Notable discrepancies** — cases where the routing decision did not match execution quality
5. **Evidence limitations** — what the synthetic registry data can and cannot tell us
6. **Findings** — any conclusions drawn from the observations
7. **Unresolved questions** — questions that emerged but were not answered
8. **Scope compliance** — explicit confirmation that the experiment stayed within scope and that
   no AI-Hub files, data, configuration, or behavior were modified
9. **Recommendations** — whether any findings warrant a separate owner-approved scope for future work

### 9.3 No Closure Now

The closure artifact is **not** created as part of this scope document. It is prepared after Task 8
is complete.

---

## 10. Stop Condition

The experiment has a **hard stop** after Task 8. No additional tasks, iterations, extensions, or
follow-on experiments are authorized by this scope.

The experiment also pauses immediately (Section 6.4) if any task requires actions outside this
scope. Such situations are recorded as findings, not solved.

---

## 11. Authority

This scope authorizes **ONLY**:

* Execution of the eight-task experiment against the existing M4 implementation
* Use of existing `route decide` and `route record` CLI operations
* Human observation and manual recording of outcomes

This scope does **NOT** authorize:

* implementation or modification of AI-Hub
* M5
* any future milestone
* any change to AI-Hub source, tests, configuration, schema, data, or behavior
* any expansion of the task set
* any automatic feedback mechanism

Any work outside this document requires a **separate owner-approved scope**.

---

## 12. Compliance Mapping

| Constitutional Principle | Compliance |
|---|---|
| Art. 1 — User Sovereignty | Experiment uses existing read-only operations; no irreversible changes made |
| Art. 2 — Recommendation Over Automation | Routing returns advice; execution remains with the human/OpenCode |
| Art. 7 — Deterministic Behaviour | Same task + same DB state → same envelope (documented input-time dependence for `created_at`) |
| Art. 8 — Traceability | `route record` appends to the provenance ledger; unrecorded decisions are ephemeral (documented) |
| Art. 10 — Truthfulness | Observations record actual outcomes; no fabricated claims about routing quality |
| Art. 11 — Documentation Before Code | This scope document precedes any experiment execution |

| Contract Section | Compliance |
|---|---|
| §12 — Feedback Governance | Observations are external/manual; no automatic score mutation; no telemetry ingestion |
| §14 — Execution-Plane Boundary | AI-Hub computes the routing decision; execution stays with OpenCode |
| §15 — Versioning | `decision_version` remains `3.1.0`; `contract_version` remains `"1"` |

---

## 13. Relationship to Prior Baselines

* This experiment consumes the M4-closed routing decision plane (`decision_version` 3.1.0,
  `contract_version` "1").
* The synthetic registry population (providers, models, benchmark scores) was loaded by the owner
  as a prerequisite; this scope does not govern that population action.
* No M1–M4 artifact is modified by this scope.
* No M1–M4 finding is reopened by this scope.

---

*End of scope document. Planning only — no implementation was started, and no production file was
touched.*
