# AI-Hub VS Code Extension (Phase 5)

A thin, read-only presentation layer for AI-Hub intelligence. It displays the
authoritative output of the AI-Hub CLI (`python -m app.main ...`) verbatim.

## Scope

* **Only reads** - the extension invokes the read-only AI-Hub CLI and renders
  its stdout; it never opens SQLite directly and never issues a mutating
  command.
* **No decision logic** - no scoring, ranking, recommendation, or fallback
  policy logic exists in this workspace. All intelligence is delegated to the
  AI-Hub backend via the CLI.
* **No settings/config/network mutation** - it does not write VS Code
  settings, AI-Hub configuration, environment variables, API keys, or make
  network requests.
* **One data-access path** - every feature maps to a `python -m app.main`
  invocation defined in `src/features.ts`.

## Features

| Command | CLI action | Input |
|---------|-----------|-------|
| AI-Hub: Provider Status | `dashboard report providers` | none |
| AI-Hub: Model Scores | `score list` | none |
| AI-Hub: Recommendations | `recommend chain --task <task>` | task |
| AI-Hub: Fallback Chain | `fallback status` | none |
| AI-Hub: Score History | `dashboard history --model <id>` | model id |
| AI-Hub: Availability History | `dashboard history --availability` | none |
| AI-Hub: Dashboard Report | `dashboard report <name>` | report name |

A Reports tree view (activity bar) lists the five dashboard reports.

## Configuration

* `ai-hub.pythonPath` - Python executable used to invoke the CLI (default
  `python`).
* `ai-hub.workingDirectory` - AI-Hub repository root serving as the CLI
  working directory (defaults to the first workspace folder).

The extension reads these values; it never writes configuration.

## Build & test (OWNER-RUN)

The npm dependency graph is isolated to this directory and is **not**
installed automatically. The owner must run:

```
cd connectors/vscode
npm install          # installs devDependencies only (typescript, @types/...)
npm run compile      # tsc -> out/
npm test            # @vscode/test-cli integration tests (downloads a VS Code instance)
```

Offline unit tests (Node built-in test runner, no npm needed):

```
npm run test:unit    # tsc -> out-test + node --test out-test/test/
```

## Layout

```
package.json            npm manifest (devDependencies only; isolated graph)
tsconfig.json           extension build
tsconfig.test.json      offline unit-test build
src/features.ts         read-only CLI feature registry (pure)
src/cli.ts              python -m app.main executor (pure)
src/present.ts          deterministic webview rendering (pure)
src/extensionCore.ts    vscode integration behind DI (testable)
src/extension.ts        thin host entry (only real `vscode` import)
test/*.test.ts          offline unit tests (node:test)
test/integration/*      @vscode/test-cli tests (owner-run)
types/*.d.ts            offline compile stubs (replaced by @types on install)
```