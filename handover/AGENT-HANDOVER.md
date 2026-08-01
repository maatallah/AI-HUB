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

Ready for Phase 1 implementation.

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

# Known Future Areas

* Provider API adapters
* Automated benchmarks
* VS Code integration
* MCP integration
* AI ecosystem discovery
* Community knowledge sharing

---

# First Implementation Goal

Create the minimum working foundation:

* repository structure
* SQLite database
* schemas
* configuration system
* manual provider registry

Do not implement automation yet.
