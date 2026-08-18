// Extension core (Phase 5) - VS Code integration behind dependency
// injection so the whole command/activation/dispatch path is unit-testable
// offline with a fake `vscode` object (no VS Code host required).
//
// This module contains presentation/integration logic ONLY:
//   * command registration and dispatch;
//   * gathering of simple inputs (task / model id / report name);
//   * invoking the read-only CLI (via the injected `runCli`);
//   * rendering authoritative CLI output verbatim (see present.ts).
// It contains no scoring, ranking, recommendation or fallback policy logic.

import { CliResult } from "./cli";
import { FEATURES, Feature, REPORT_NAMES } from "./features";
import { renderError, renderReport } from "./present";

interface Disposable {
  dispose(): void;
}

interface WebviewPanel {
  readonly webview: { html: string };
  title: string;
  onDidDispose(cb: () => void): Disposable;
  dispose(): void;
}

interface TreeItem {
  label: string;
  description?: string;
  command?: { command: string; title: string; arguments: unknown[] };
}

interface VscodeApi {
  ViewColumn: { Active: number };
  commands: {
    registerCommand(
      command: string,
      handler: (...args: unknown[]) => unknown
    ): Disposable;
  };
  window: {
    showInputBox(options: {
      prompt?: string;
      placeHolder?: string;
      validateInput?: (value: string) => string | undefined;
    }): Thenable<string | undefined>;
    showQuickPick(
      items: readonly { label: string }[] | Thenable<readonly { label: string }[]>
    ): Thenable<{ label: string } | undefined>;
    createWebviewPanel(
      viewType: string,
      title: string,
      column: unknown,
      options: { enableScripts: boolean }
    ): WebviewPanel;
    showErrorMessage(message: string): Thenable<string | undefined>;
    createTreeView(
      viewId: string,
      options: { treeDataProvider: TreeDataProvider }
    ): unknown;
  };
}

interface TreeDataProvider {
  getChildren(element?: string): string[] | Thenable<string[]>;
  getTreeItem(element: string): TreeItem | Thenable<TreeItem>;
}

export interface ExtensionRuntime {
  readonly config: { get(key: string, fallback: string): string };
  readonly workingDirectory: () => string;
  readonly runCli: (
    pythonPath: string,
    cwd: string,
    args: string[]
  ) => Promise<CliResult>;
}

export function createExtension(vscode: VscodeApi, runtime: ExtensionRuntime) {
  const panels = new Map<string, WebviewPanel>();

  function showPanel(title: string, html: string): void {
    const existing = panels.get(title);
    if (existing) {
      existing.webview.html = html;
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      "ai-hub.report",
      title,
      vscode.ViewColumn.Active,
      { enableScripts: false }
    );
    panel.webview.html = html;
    panel.onDidDispose(() => panels.delete(title));
    panels.set(title, panel);
  }

  async function dispatch(feature: Feature, preset?: string): Promise<void> {
    const input = await resolveInput(vscode, feature, preset);
    if (input === undefined) {
      return; // user cancelled
    }
    const cwd = runtime.workingDirectory();
    const python = runtime.config.get("pythonPath", "python");
    const result = await runtime.runCli(python, cwd, feature.buildArgs(input));
    if (result.exitCode !== 0) {
      const message =
        result.stderr.trim() || result.stdout.trim() || "AI-Hub CLI failed.";
      vscode.window.showErrorMessage(`${feature.title}: ${message}`);
      showPanel(feature.title, renderError(feature.title, message));
      return;
    }
    showPanel(feature.title, renderReport(feature.title, result.stdout));
  }

  return {
    activate(context: { subscriptions: unknown[] }): void {
      for (const feature of FEATURES) {
        context.subscriptions.push(
          vscode.commands.registerCommand(feature.commandId, (preset?: unknown) =>
            dispatch(feature, typeof preset === "string" ? preset : undefined)
          )
        );
      }
      context.subscriptions.push(
        vscode.window.createTreeView("ai-hub.reports", {
          treeDataProvider: {
            getChildren: (element?: string): string[] =>
              element === undefined ? [...REPORT_NAMES] : [],
            getTreeItem: (label: string): TreeItem => ({
              label,
              description: "dashboard report",
              command: {
                command: "ai-hub.dashboardReport",
                title: "Open report",
                arguments: [label],
              },
            }),
          },
        })
      );
    },
  };
}

async function resolveInput(
  vscode: VscodeApi,
  feature: Feature,
  preset?: string
): Promise<string | undefined> {
  switch (feature.requiresInput) {
    case "none":
      return "";
    case "task":
      return (
        preset ??
        (await vscode.window.showInputBox({
          prompt: `Task for ${feature.title}`,
          placeHolder: "e.g. python web service",
        }))
      );
    case "model_id": {
      const valid = /^\d+$/;
      let value = preset;
      if (value === undefined) {
        value = await vscode.window.showInputBox({
          prompt: `Model id for ${feature.title}`,
          placeHolder: "e.g. 1",
          validateInput: (v: string): string | undefined =>
            valid.test(v) ? undefined : "Model id must be a positive integer.",
        });
      }
      if (value === undefined) {
        return undefined;
      }
      if (!valid.test(value)) {
        vscode.window.showErrorMessage(
          `${feature.title}: invalid model id '${value}'.`
        );
        return undefined;
      }
      return value;
    }
    case "report": {
      if (preset !== undefined && (REPORT_NAMES as readonly string[]).includes(preset)) {
        return preset;
      }
      const picked = await vscode.window.showQuickPick(
        REPORT_NAMES.map((label) => ({ label }))
      );
      if (picked === undefined) {
        return undefined;
      }
      if (!(REPORT_NAMES as readonly string[]).includes(picked.label)) {
        vscode.window.showErrorMessage(
          `${feature.title}: unknown report '${picked.label}'.`
        );
        return undefined;
      }
      return picked.label;
    }
    default:
      return undefined;
  }
}