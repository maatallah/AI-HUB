// Thin VS Code host entry point (Phase 5).
//
// This is the ONLY file that imports the real `vscode` module. It wires the
// host API to the testable extension core (extensionCore.ts) and resolves two
// runtime values (python path and working directory) from the workspace. All
// display/integration logic lives in extensionCore.ts.

import * as vscode from "vscode";
import { runCli } from "./cli";
import { createExtension, ExtensionRuntime } from "./extensionCore";

const extension = createExtension(vscode, hostRuntime());

export function activate(context: vscode.ExtensionContext): void {
  extension.activate(context);
}

export function deactivate(): void {
  // Nothing to tear down; all disposables are owned by the activation context.
}

function hostRuntime(): ExtensionRuntime {
  return {
    config: {
      get(key: string, fallback: string): string {
        const cfg = vscode.workspace.getConfiguration("ai-hub");
        const value = cfg.get<string>(key);
        return value && value.trim() !== "" ? value : fallback;
      },
    },
    workingDirectory(): string {
      const configured = vscode.workspace
        .getConfiguration("ai-hub")
        .get<string>("workingDirectory");
      if (configured && configured.trim() !== "") {
        return configured;
      }
      const folder = vscode.workspace.workspaceFolders?.[0];
      return folder ? folder.uri.fsPath : process.cwd();
    },
    runCli,
  };
}