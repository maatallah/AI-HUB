// Tests for the extension core: activation, command registration and
// dispatch, deterministic display, failure handling and mutation guards.
// Runs fully offline with a fake `vscode` object and an injected CLI runner.

import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import { CliResult } from "../src/cli";
import { createExtension } from "../src/extensionCore";
import { FEATURES } from "../src/features";

interface Panel {
  title: string;
  html: string;
  disposed: boolean;
  setOnDispose: (cb: () => void) => void;
  onDidDispose(cb: () => void): { dispose(): void };
  dispose(): void;
  webview: { html: string };
}

function fakeVscode(overrides: Record<string, unknown> = {}) {
  const panels: Panel[] = [];
  const registered: { command: string; handler: (...a: unknown[]) => unknown }[] = [];
  const messages: string[] = [];
  let inputResult: string | undefined;
  let pickLabel: string | undefined;

  const vscode = {
    ViewColumn: { Active: -1 },
    commands: {
      registerCommand(command: string, handler: (...a: unknown[]) => unknown) {
        registered.push({ command, handler });
        return { dispose() {} };
      },
    },
    window: {
      createWebviewPanel(eventType: string, title: string, _col: unknown) {
        const panel: Panel = {
          title, html: "", disposed: false,
          setOnDispose: () => {},
          onDidDispose: (cb: () => void) => {
            panel.setOnDispose = () => cb();
            return { dispose() {} };
          },
          dispose() { panel.disposed = true; },
          webview: { html: "" },
        };
        panels.push(panel);
        return panel;
      },
      showInputBox: async (): Promise<string | undefined> => inputResult,
      showQuickPick: async (): Promise<{ label: string } | undefined> =>
        pickLabel === undefined ? undefined : { label: pickLabel },
      showErrorMessage: (m: string) => { messages.push(m); return Promise.resolve(undefined); },
      createTreeView: () => ({ dispose() {} }),
    },
    workspace: { getConfiguration: () => ({ get: (_k: string, d: string) => d }) },
  };
  return {
    vscode: Object.assign(vscode, overrides),
    panels,
    registered,
    messages,
    setInput: (value?: string) => { inputResult = value; },
    setPick: (label?: string) => { pickLabel = label; },
  };
}

function fakeRuntime(
  cli?: (args: string[]) => CliResult | Promise<CliResult>
) {
  const calls: string[][] = [];
  return {
    config: { get: (_k: string, d: string) => d },
    workingDirectory: () => "C:/repo",
    runCli: async (python: string, cwd: string, args: string[]) => {
      calls.push(args);
      return cli ? await cli(args)
        : { exitCode: 0, stdout: "ok\n", stderr: "" };
    },
    calls,
  };
}

test("activate registers all seven commands and the tree view", () => {
  const h = fakeVscode();
  const ext = createExtension(h.vscode, fakeRuntime());
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const ids = h.registered.map((r) => r.command).sort();
  assert.deepStrictEqual(ids, FEATURES.map((f) => f.commandId).sort());
  assert.strictEqual(context.subscriptions.length, FEATURES.length + 1);
});

test("dispatch for a no-input feature shows CLI stdout verbatim", async () => {
  const h = fakeVscode();
  const rt = fakeRuntime(() => ({ exitCode: 0, stdout: "# providers\n1\tAcme <ok>", stderr: "" }));
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.status")!.handler;
  await handler();
  assert.strictEqual(h.panels.length, 1);
  assert.strictEqual(h.panels[0].title, "Provider Status");
  assert.ok(h.panels[0].webview.html.includes("&lt;ok&gt;"));
  assert.deepStrictEqual(rt.calls, [["dashboard", "report", "providers"]]);
});

test("re-dispatch reuses the panel (deterministic same title)", async () => {
  const h = fakeVscode();
  const rt = fakeRuntime(() => ({ exitCode: 0, stdout: "a\n", stderr: "" }));
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.status")!.handler;
  await handler();
  await handler();
  assert.strictEqual(h.panels.length, 1);
});

test("recommendations uses the task input box", async () => {
  const h = fakeVscode();
  h.setInput("python web app");
  const rt = fakeRuntime();
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.recommendations")!.handler;
  await handler();
  assert.deepStrictEqual(rt.calls, [["recommend", "chain", "--task", "python web app"]]);
});

test("user cancels input -> no CLI call, no error", async () => {
  const h = fakeVscode();
  h.setInput(undefined);
  const rt = fakeRuntime();
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.recommendations")!.handler;
  await handler();
  assert.strictEqual(rt.calls.length, 0);
  assert.strictEqual(h.messages.length, 0);
});

test("invalid model id is rejected (no CLI call)", async () => {
  const h = fakeVscode();
  h.setInput("abc");
  const rt = fakeRuntime();
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.scoreHistory")!.handler;
  await handler();
  assert.strictEqual(rt.calls.length, 0);
  assert.ok(h.messages.some((m) => m.includes("invalid model id")));
});

test("underlying CLI failure shows an error and error panel (isError path)", async () => {
  const h = fakeVscode();
  const rt = fakeRuntime(() => ({ exitCode: 3, stdout: "", stderr: "Database not found" }));
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.status")!.handler;
  await handler();
  assert.ok(h.messages.some((m) => m.includes("Database not found")));
  assert.strictEqual(h.panels.length, 1);
  assert.ok(h.panels[0].webview.html.includes("Database not found"));
});

test("unknown report from quick pick is rejected", async () => {
  const h = fakeVscode();
  h.setPick("bogus");
  const rt = fakeRuntime();
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.dashboardReport")!.handler;
  await handler();
  assert.strictEqual(rt.calls.length, 0);
  assert.ok(h.messages.some((m) => m.includes("unknown report")));
});

test("dashboard report preset from the tree view dispatches directly", async () => {
  const h = fakeVscode();
  const rt = fakeRuntime(() => ({ exitCode: 0, stdout: "# overview\n1", stderr: "" }));
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.dashboardReport")!.handler;
  await handler("overview");
  assert.deepStrictEqual(rt.calls, [["dashboard", "report", "overview"]]);
});

function sourceOf(relative: string): string {
  // Test compiles into connectors/vscode/out-test/test; repo source lives
  // two levels up.
  return readFileSync(join(__dirname, "../../", relative), "utf-8");
}

const PREVENTED_SURFACES = [
  // No settings/config mutation surface should exist in the core.
  ".update(",
  "settings.json",
  "workspace.getConfiguration",
];

test("extension core has no settings/config mutation surface", () => {
  const source = sourceOf("src/extensionCore.ts");
  for (const needle of PREVENTED_SURFACES) {
    assert.ok(!source.includes(needle), `extensionCore must not contain ${needle}`);
  }
});

test("extension core contains no network or API-key handling", () => {
  const source = sourceOf("src/extensionCore.ts");
  const forbidden = ["http", "apiKey", "api_key", "token", "secret", "fetch"];
  for (const needle of forbidden) {
    assert.ok(!source.toLowerCase().includes(needle), `extensionCore must not contain ${needle}`);
  }
});

test("extension core imports only its three allowed peer modules", () => {
  const source = sourceOf("src/extensionCore.ts");
  const imports = source
    .split("\n")
    .filter((l) => l.trim().startsWith("import ") || l.trim().startsWith("from "))
    .join("\n");
  const allowed = ["./cli", "./features", "./present"];
  for (const line of source.split("\n")) {
    const m = line.match(/from\s+"([^"]+)"/);
    if (m) {
      assert.ok(
        allowed.includes(m[1]),
        `extensionCore imports unexpected module ${m[1]}`
      );
    }
  }
  // No SQL, no decision math, no network primitives.
  assert.ok(!source.includes("sqlite"));
  assert.ok(!source.includes("fetch("));
  assert.ok(!source.includes("child_process"));
});

test("empty CLI stdout renders the no-data notice (never fabricated)", async () => {
  const h = fakeVscode();
  const rt = fakeRuntime(() => ({ exitCode: 0, stdout: "", stderr: "" }));
  const ext = createExtension(h.vscode, rt);
  const context = { subscriptions: [] as unknown[] };
  ext.activate(context);
  const handler = h.registered.find((r) => r.command === "ai-hub.modelScores")!.handler;
  await handler();
  assert.strictEqual(h.messages.length, 0); // success: empty is valid no-data
  assert.ok(h.panels[0].webview.html.includes("(no data)"));
});