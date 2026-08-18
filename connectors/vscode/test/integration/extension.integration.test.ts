// VS Code API integration tests (Phase 5).
//
// These run inside a real VS Code host via `vscode-test` (@vscode/test-cli;
// owner-run: requires `npm install` inside connectors/vscode, which also
// downloads a VS Code test instance). They complement the offline unit tests
// in test/features.test.ts, test/cli.test.ts, test/present.test.ts and
// test/extensionCore.test.ts.
//
// The @vscode/test-cli runner loads this file with mocha (tdd UI), so the
// suite/test below must be registered at module top level.

import * as assert from "node:assert";
import * as vscode from "vscode";

const extensionId = "ai-hub.ai-hub";

const commandIds = [
  "ai-hub.status",
  "ai-hub.modelScores",
  "ai-hub.recommendations",
  "ai-hub.fallbackChain",
  "ai-hub.scoreHistory",
  "ai-hub.availabilityHistory",
  "ai-hub.dashboardReport",
];

function extension(): vscode.Extension<unknown> {
  const ext = vscode.extensions.getExtension(extensionId);
  assert.ok(ext, `extension ${extensionId} should be loaded`);
  return ext!;
}

suite("AI-Hub extension (integration)", () => {
  test("activates and registers all commands", async () => {
    const ext = extension();
    await ext.activate();
    assert.ok(ext.isActive, "extension should be active after activate()");
    const registered = await vscode.commands.getCommands();
    for (const id of commandIds) {
      assert.ok(registered.includes(id), `expected ${id} to be registered`);
    }
  });

  test("status command executes without throwing", async () => {
    const ext = extension();
    await ext.activate();
    const result = await vscode.commands.executeCommand("ai-hub.status");
    assert.ok(result === undefined || result === null);
  });
});