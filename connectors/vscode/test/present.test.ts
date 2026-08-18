// Tests for the deterministic presentation layer.

import { strict as assert } from "node:assert";
import test from "node:test";

import { escapeHtml, renderError, renderReport } from "../src/present";

test("escapeHtml escapes every HTML metacharacter", () => {
  const out = escapeHtml(`<a>&"'"</a>`);
  assert.ok(!out.includes("<"));
  assert.ok(!out.includes(">"));
  assert.ok(!out.includes('"'));
  assert.ok(!out.includes("'"));
  // The lone `&` becomes an entity; any remaining `&` must start an entity.
  assert.ok(out.includes("&lt;"));
  assert.ok(out.includes("&amp;"));
  assert.ok(out.includes("&quot;"));
  assert.ok(out.includes("&#39;"));
});

test("renderReport wraps escaped stdout in a code block", () => {
  const html = renderReport("Provider Status", "# providers\nid\tname\n1\tAcme <hot>");
  assert.ok(html.includes("Provider Status"));
  assert.ok(html.includes("&lt;hot&gt;")); // escaped output present
  assert.ok(!html.includes("Acme <hot>")); // raw output must be escaped
  assert.ok(html.includes("# providers")); // harmless text passes through
});

test("renderReport with empty output shows stable no-data notice", () => {
  const html = renderReport("Model Scores", "   \n");
  assert.ok(html.includes("(no data)"));
});

test("renderReport is deterministic (no timestamps or dynamic content)", () => {
  const body = "x\ty\n1\t2\n";
  const first = renderReport("Scores", body);
  const second = renderReport("Scores", body);
  assert.strictEqual(first, second);
  assert.ok(!first.includes("Date("));
  assert.ok(first.startsWith("<!DOCTYPE html>"));
});

test("renderError surfaces the message verbatim", () => {
  const html = renderError("Score History", "Error: boom <details>");
  assert.ok(html.includes("Error: boom"));
  assert.ok(html.includes("&lt;details&gt;")); // escaped and script-free
});