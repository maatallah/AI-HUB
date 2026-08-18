// Tests for the feature registry (read-only CLI command mapping).

import { strict as assert } from "node:assert";
import test from "node:test";

import {
  FEATURES,
  REPORT_NAMES,
  featureByCommand,
  isValidReportName,
} from "../src/features";

test("features exposes exactly the seven Phase 5 features", () => {
  assert.strictEqual(FEATURES.length, 7);
  const ids = FEATURES.map((f) => f.commandId).sort();
  assert.deepStrictEqual(ids, [
    "ai-hub.availabilityHistory",
    "ai-hub.dashboardReport",
    "ai-hub.fallbackChain",
    "ai-hub.modelScores",
    "ai-hub.recommendations",
    "ai-hub.scoreHistory",
    "ai-hub.status",
  ]);
});

test("every feature builds read-only argument lists via -m app.main", () => {
  for (const f of FEATURES) {
    const args = f.buildArgs(f.requiresInput === "none" ? "" : "1");
    assert.ok(Array.isArray(args));
    assert.ok(args.length >= 2, `${f.commandId} should pass a CLI subcommand`);
    assert.ok(
      args[0] === "dashboard" || args[0] === "score" ||
        args[0] === "recommend" || args[0] === "fallback",
      `${f.commandId} uses a known read-only CLI subcommand`
    );
  }
});

test("no feature maps to a mutating CLI subcommand", () => {
  for (const f of FEATURES) {
    const args = f.buildArgs("1");
    const top = args[0];
    assert.ok(
      !["provider", "init-db", "monitor", "config"].includes(top),
      `${f.commandId} must not use mutating top-level subcommand '${top}'`
    );
    assert.ok(
      !(top === "score" && args[1] === "set"),
      `${f.commandId} must not write scores`
    );
    assert.ok(
      !(top === "recommend" && args[1] === "top"),
      `${f.commandId} must not record provenance (recommend top)`
    );
  }
});

test("recommendations use recommend chain (no provenance write)", () => {
  const rec = featureByCommand("ai-hub.recommendations");
  assert.deepStrictEqual(rec.buildArgs("python web app"), [
    "recommend", "chain", "--task", "python web app",
  ]);
});

test("featureByCommand handles unknown ids", () => {
  assert.throws(() => featureByCommand("ai-hub.nope"));
});

test("report names are the five dashboard reports", () => {
  assert.deepStrictEqual([...REPORT_NAMES].sort(), [
    "monitoring", "overview", "providers", "recommendations", "scores",
  ]);
  assert.ok(isValidReportName("overview"));
  assert.ok(!isValidReportName("bogus"));
});