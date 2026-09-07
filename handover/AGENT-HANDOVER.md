# handover/AGENT-HANDOVER.md

# AI-Hub Agent Handover Document

## Purpose

This document allows a new AI agent or contributor to understand the project without access to previous conversations.

The repository documentation is the only source of truth.

---

# Project Identity

Name:

AI-Hub

Type:

Personal AI Provider Intelligence and Orchestration Platform

Mission:

Create an independent intelligence layer that monitors AI providers, evaluates models, recommends suitable AI resources, and generates safe fallback strategies.

---

# Current Version

Architecture:

v1.1

Implementation Specification:

v1.2

Status:

Phases 1–6 released. Post-v1 adaptive routing M1–M4 complete (`decision_version`
3.1.0). Real-world routing experiment closed (Tasks 1–7 PASS, Task 8 BLOCKED —
target function not specified by approved scope). No M5 authorized. Current
state: reconciliation/documentation corrections in progress (see
`docs/review/POST-V1-RECONCILIATION-CORRECTIONS.md`).

---

# Core Philosophy

AI-Hub does not replace AI assistants.

AI-Hub does not control development environments.

AI-Hub helps users decide:

* which AI to use
* when to switch
* why a recommendation was made
* what alternatives exist

---

# Important Architectural Decisions

## Repository Independence

AI-Hub is not attached to any application repository.

Examples:

Not:

```
MediCab/AI-Hub
CMMS/AI-Hub
```

Instead:

```
M:\dev\AI-Hub
```

---

## No Automatic Configuration Changes

AI-Hub never modifies:

* VS Code settings
* config files
* API keys
* environment variables
* installed extensions

---

## Provider History Preservation

Providers are archived.

They are not silently deleted.

Historical information is part of the intelligence system.

---

# Main Components

## Core

Responsible for:

* data models
* business rules
* recommendation logic

---

## Database

Stores:

* providers
* models
* availability
* events
* preferences
* decisions

---

## Monitoring Engine

Responsible for:

* provider health
* quota state
* ecosystem changes

---

## Recommendation Engine

Responsible for:

* scoring
* ranking
* explanations

---

## Fallback Engine

Responsible for:

* alternative provider chains
* deterministic ordering

---

## Dashboard

Responsible for:

* visibility
* reporting
* human interaction

---

## Connectors

Examples:

* VS Code
* MCP
* future integrations

Connectors consume AI-Hub.

They do not contain decision logic.

---

# Implementation Rules

A contributor must:

1. Read specifications before coding.
2. Avoid undocumented behaviour.
3. Create ADRs for architectural changes.
4. Keep modules independent.
5. Maintain explainability.

---

# Implemented Capabilities

The following are implemented and released:

* Phase 1 — Repository Foundation (baseline `7ceac80`)
* Phase 2 — Monitoring Engine (health checks, availability/lifecycle, quota, validation)
* Phase 3 — Scoring / Recommendation / Fallback (scoring engine, recommendation with provenance, fallback chain)
* Phase 4 — Dashboard / Reporting / History (read-only aggregation, deterministic reports, append-only event history)
* Phase 5 — Connectors (VS Code extension, MCP server over stdio, shared read-only adapter)
* Phase 6 — Ecosystem Intelligence (discovery candidates, benchmark ingestion, approval materialization, model registry, trend analysis)
* Post-v1 Adaptive Routing M1–M4 (read-only DECIDE, append-only RECORD, cost-direction fix, config/template alignment)

---

# Known Future Areas

* M5 adaptive learning — **NOT AUTHORIZED** (requires explicit owner authorization and new scope definition)
* Community knowledge sharing

---

# First Implementation Goal (Historical — Completed)

The first implementation goal was to create the minimum working foundation:

* repository structure
* SQLite database
* schemas
* configuration system
* manual provider registry

This was completed as Phase 1 (baseline `7ceac80`). It is retained here for
historical reference only. Do not treat this as a current objective.
