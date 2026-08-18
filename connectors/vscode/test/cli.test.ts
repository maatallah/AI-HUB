// Tests for the read-only CLI executor.

import { strict as assert } from "node:assert";
import test from "node:test";

import { ExecFn, runCli } from "../src/cli";

type ExecCallback = (
  error: Error & { code?: number | string } | null,
  stdout: string,
  stderr: string
) => void;

function fakeExec(execute: (callback: ExecCallback) => void): ExecFn {
  return (_file, _args, _options, callback) => execute(callback as ExecCallback);
}

test("runCli builds python -m app.main arguments and returns exit 0", async () => {
  let called_file = "";
  let called_args: readonly string[] = [];
  const exec: ExecFn = (file, args, _options, callback) => {
    called_file = file;
    called_args = args;
    callback(null, "# providers\nid\tname", "");
  };
  const result = await runCli("python", "C:/repo", ["dashboard", "report", "providers"], 1000, exec);
  assert.strictEqual(called_file, "python");
  assert.deepStrictEqual(called_args, ["-m", "app.main", "dashboard", "report", "providers"]);
  assert.strictEqual(result.exitCode, 0);
  assert.strictEqual(result.stdout, "# providers\nid\tname");
  assert.strictEqual(result.stderr, "");
});

test("runCli maps numeric exit codes", async () => {
  const result = await runCli(
    "python", "C:/repo", ["dashboard", "report", "x"],
    1000,
    fakeExec((cb) =>
      cb(Object.assign(new Error("exit"), { code: 2 }), "", "bad"))
  );
  assert.strictEqual(result.exitCode, 2);
  assert.strictEqual(result.stderr, "bad");
});

test("runCli maps non-numeric errors to exit 1", async () => {
  const result = await runCli(
    "python", "C:/repo", ["dashboard", "report", "x"],
    1000,
    fakeExec((cb) => cb(new Error("ENOENT"), "", ""))
  );
  assert.strictEqual(result.exitCode, 1);
});