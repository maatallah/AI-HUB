# POST-V1 ROUTING — REAL-WORLD EXPERIMENT CLOSURE

Status: **CLOSURE RECORD**
Baseline: M4 closure `1a465f384071f5eca361463fd97037b93a3998b1` (`decision_version` 3.1.0 active;
548/548 tests passing)
Date: 2026-09-03
Nature: Formal closure of the first post-M4 real-world routing experiment. This document records
observed results only. It does **not** authorize M5, adaptive learning, feedback ingestion,
telemetry collection, scoring changes, routing changes, or any other implementation work.

Governing documents:

* Approved experiment scope: `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-SCOPE.md`
* `CONSTITUTION.md` — permanent principles (Arts. 1–12)
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — normative contract; §12 feedback
  governance boundary; §14 execution-plane boundary
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` — approved decision record; Option A
  decision-plane-only boundary is binding

---

## 1. Purpose

This document formally closes the first post-M4 real-world routing experiment and records its
observed results.

The experiment evaluated the existing M1–M4 decision plane by running `route decide` against
8 predefined real OpenCode tasks and recording routing provenance via `route record`.

M5/adaptive learning was **not** authorized. The experiment is an observation of existing
behavior, not a test of new capabilities.

---

## 2. Scope

The approved experiment scope is:

`docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-SCOPE.md`

The approved task list (exactly 8 tasks, closed set):

| # | Task Description | Profile | Constraints |
|---|---|---|---|
| 1 | Write a Python function that reads a CSV file and returns a list of dictionaries. | `coding` | (none) |
| 2 | Explain the difference between TCP and UDP, including when to use each. | `reasoning` | (none) |
| 3 | Generate a short email greeting for a meeting reminder. | `free` | (none) |
| 4 | Summarize the contents of this repository's `CONSTITUTION.md` file. | `long_context` | (none) |
| 5 | Describe what you see in a supplied screenshot. | `coding` | `required_capabilities: [vision]` |
| 6 | Write a Python one-liner that filters even numbers from a list. | `coding` | (none) |
| 7 | Process a 500KB text file and extract all unique words. | `coding` | `min_context_window: 500000` |
| 8 | Refactor a specific function from the codebase to use async/await. | `coding` | (none) |

---

## 3. Experiment Outcome

**COMPLETE WITH BLOCKED TASK**

Tasks 1–7 were executed and recorded. Task 8 was not executed because its target function was
never specified by the approved scope or authoritative experiment materials.

---

## 4. Task-by-Task Results

| Task | Profile / Constraints | Selected Provider / Model | Decision ID | Execution Status | Classification |
|------|----------------------|---------------------------|-------------|------------------|----------------|
| 1 | `coding` / none | EnterpriseHF / enterprise-hf | `c485c098-571b-4418-bac6-ecceb8f7fdcb` | Executed | PASS |
| 2 | `reasoning` / none | Acme Reasoning / acme-reasoning-x | `81ea0603-ba6f-4a66-adec-9892e0480d3c` | Executed | PASS |
| 3 | `free` / none | Velocita / velocita-fast | `d7329006-19b9-455d-a911-c18a002e6810` | Executed | PASS |
| 4 | `long_context` / none | LargeModel / large-model-premium | `e013a2d1-d818-4758-beeb-2a7d18fee640` | Executed | PASS |
| 5 | `coding` / `required_capabilities: [vision]` | EnterpriseHF / enterprise-hf | `cf1aa2ae-e86b-45e2-9488-9d84d2c6b4f3` | Executed | PASS |
| 6 | `coding` / none | EnterpriseHF / enterprise-hf | `d8590730-b10e-4921-a631-0d0fed8af043` | Executed | PASS |
| 7 | `coding` / `min_context_window: 500000` | LargeModel / large-model-premium | `0ea0da61-1f59-4a77-a771-0ed109aa07c2` | Executed | PASS |
| 8 | `coding` / none | — | — | BLOCKED | BLOCKED |

---

## 5. Routing and Provenance Results

The experiment produced:

* **7 routing decisions** (Tasks 1–7); Task 8 generated no routing decision
* **60 recommendation rows** persisted in `database/ai_hub.db` (original executions + re-runs for Tasks 5 and 6)
* **60 `RECOMMENDATION_CREATED` events** appended to the provenance ledger
* Every executed task's DECIDE output was subsequently recorded via `route record`
* Task 5 and Task 6 were re-run with corrected procedures; their re-run decision IDs supersede the originals
* No orphaned records or missing events were identified

Individual decision IDs:

| Task | Decision ID | Provider | Model | Score | Rank | Eligible |
|------|-------------|----------|-------|-------|------|----------|
| 1 | `c485c098-571b-4418-bac6-ecceb8f7fdcb` | EnterpriseHF | enterprise-hf | 64.0 | 0 | 9 |
| 2 | `81ea0603-ba6f-4a66-adec-9892e0480d3c` | Acme Reasoning | acme-reasoning-x | 65.75 | 0 | 9 |
| 3 | `d7329006-19b9-455d-a911-c18a002e6810` | Velocita | velocita-fast | 74.2 | 0 | 9 |
| 4 | `e013a2d1-d818-4758-beeb-2a7d18fee640` | LargeModel | large-model-premium | 82.4 | 0 | 9 |
| 5 | `cf1aa2ae-e86b-45e2-9488-9d84d2c6b4f3` | EnterpriseHF | enterprise-hf | 64.0 | 0 | 4 |
| 6 | `d8590730-b10e-4921-a631-0d0fed8af043` | EnterpriseHF | enterprise-hf | 64.0 | 0 | 9 |
| 7 | `0ea0da61-1f59-4a77-a771-0ed109aa07c2` | LargeModel | large-model-premium | 63.8 | 0 | 1 |

Task 8 generated no routing decision because execution was blocked before routing.

---

## 6. Constraint Enforcement

Two hard constraints were tested during the experiment:

| Task | Constraint | Effect | Eligible (before → after) |
|------|-----------|--------|---------------------------|
| 5 | `required_capabilities: [vision]` | Eliminated providers without vision capability | 9 → 4 |
| 7 | `min_context_window: 500000` | Eliminated models with insufficient context window | 9 → 1 |

Task 7 had no eligible fallback model after the context constraint was applied. The routing
decision selected the only eligible candidate (LargeModel / large-model-premium).

---

## 7. Executor / Routing-Plane Boundary

The executing agent (OpenCode) continued to use `mimo-v2-5-free` for all 7 executed tasks.
No model handoff occurred.

| Field | Value |
|-------|-------|
| Executor model | `mimo-v2-5-free` (all tasks) |
| AI-Hub recommended models | enterprise-hf, acme-reasoning-x, velocita-fast, large-model-premium |
| Model handoff occurred | No |
| Execution quality affected | No — all tasks completed successfully using the executor's own model |

This is an **architectural limitation** exposed by the experiment. AI-Hub computes routing
recommendations; the executing agent retains full control over which model actually runs. Whether
this represents a product deficiency depends on the intended future role of AI-Hub — advisory
recommendation versus actual model handoff. The experiment itself does **not** establish that
implementation work is required. The experiment evaluated routing decisions and provenance — not
the recommended providers' actual task outputs.

---

## 8. Observed Findings

The following findings are evidence-supported observations. None authorize implementation changes.

### 8.1 Routing Profile Differentiation

The four routing profiles exercised in the experiment produced distinct top-ranked models. Profile weights meaningfully affect routing outcomes. The `reasoning` profile elevated Acme Reasoning; the `free` profile elevated Velocita (cost-weighted); the `long_context` profile elevated LargeModel (context-weighted).

### 8.2 Hard Constraint Enforcement

Both tested constraints (`required_capabilities`, `min_context_window`) correctly reduced the
eligible candidate set. The context-window constraint was the most restrictive, reducing 9
eligible models to 1.

### 8.3 Deterministic Behavior

The same profile + same DB state produced identical routing decisions across repeated runs.
Tasks 1 and 6, both using the `coding` profile with no constraints, selected the same
top-ranked model (EnterpriseHF / enterprise-hf) with the same score (64.0) and the same
fallback chain order.

### 8.4 Append-Only Provenance

All 60 routing recommendations were successfully persisted via `route record`. Each RECORD
operation produced exactly the expected `RECOMMENDATION_CREATED` events. No existing records
were modified or deleted. The provenance ledger remained append-only throughout.

### 8.5 Execution-Plane Gap

AI-Hub recommended providers/models for each task, but the executing agent (OpenCode) used its
own model (`mimo-v2-5-free`) in every case. This means the experiment cannot directly evaluate
the quality of the recommended providers' outputs. The routing recommendation is a suggestion;
the execution plane decides independently. This is an architectural limitation, not a defect
established by this experiment. No engineering change is authorized or required as a consequence
of this finding.

### 8.6 Observation Discipline

All observations were recorded externally. No `USER_FEEDBACK` events were created. No automatic
score mutations occurred. No telemetry was ingested. The experiment respected the contract §12
feedback governance boundary.

---

## 9. Task 8 Specification Finding

The approved experiment authorizes Task 8 in principle but does not specify which function is
to be refactored.

Read-only verification found no authoritative specification for:

* function name
* file path
* module
* class
* function signature
* selection criterion

The only Task 8 reference in any experiment material was the scope document itself, which
states: "Refactor a specific function from the codebase to use async/await."

Independently selecting a function would introduce an unstated task parameter and therefore
expand the approved experiment scope. Per §6.2 of the experiment scope, this is prohibited
without a separate owner-approved scope.

The correct disposition is:

**BLOCKED — TARGET FUNCTION NOT SPECIFIED BY APPROVED EXPERIMENT SCOPE**

This is a **specification and process lesson** for future experiment design: task definitions
must include complete target specifications. It is already recorded as a BLOCKED finding in
this closure document and does not constitute an outstanding defect requiring reopening of
this experiment.

---

## 10. Scope Compliance

* No unauthorized scope extension occurred
* No unauthorized source/configuration changes occurred
* No unauthorized routing/record operations occurred
* Only the authorized append-only `route record` mutations occurred during execution
* Task 8 was correctly stopped rather than completed by assumption

---

## 11. Repository Integrity

| Field | Value |
|-------|-------|
| Current HEAD | `a3535a5` (this closure commit) |
| Experiment scope baseline | `e4698a2` |
| M4 closure baseline | `1a465f384071f5eca361463fd97037b93a3998b1` |
| Branch | `main` |
| Pre-existing uncommitted changes | `.gitignore`, `CONSTITUTION.md`, `README.md`, `config.toml`, `handover/AGENT-HANDOVER.md` — all untouched by experiment |
| Untracked files (pre-existing) | 4 synthetic data artifacts — untouched by experiment |
| New files attributable to experiment | `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-CLOSURE.md` (this document) |

No AI-Hub source, configuration, schema, registry, or governance files were modified by the
experiment. The only experiment-related repository change is this closure document.

---

## 12. Evidence Limitations

The routing recommendations were not executed by the recommended providers/models because
OpenCode continued executing with `mimo-v2-5-free`.

Therefore the experiment evaluates:

**routing decisions + provenance + execution workflow**

but does **not** provide a direct quality comparison of the recommended providers' actual task
outputs.

Any future evaluation of recommended provider quality would require a separate experiment that
includes actual provider/model execution.

---

## 13. Unresolved Questions / Follow-up

* Task 8 target function remains unspecified. Any future execution of Task 8 requires a
  separately authorized clarification or scope decision. This is a process lesson, not an
  outstanding defect.
* The execution-plane gap is an architectural limitation. Whether to implement model handoff
  is a product decision outside the scope of this experiment. No engineering change is
  authorized or required as a consequence of this experiment.

---

## 14. Closure Statement

The experiment is formally closed as:

**COMPLETE WITH BLOCKED TASK**

* Tasks 1–7: **PASS**
* Task 8: **BLOCKED — TARGET FUNCTION NOT SPECIFIED BY APPROVED EXPERIMENT SCOPE**

This closure does **not** authorize M5, adaptive routing, feedback, telemetry, score mutation,
routing algorithm changes, or any other implementation work. Any such work requires a separate
owner-approved scope.

---

*End of experiment closure record.*
