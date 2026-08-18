// Read-only AI-Hub CLI executor (Phase 5).
//
// The extension obtains AI-Hub data ONLY by invoking the AI-Hub CLI
// (`python -m app.main ...`) as a child process and returning its stdout.
// There is exactly one data-access path (see features.ts). This module never
// modifies files, never writes to the database, never touches configuration
// and never contacts the network.

import { execFile } from "node:child_process";
import type { ExecFileException } from "node:child_process";

export interface CliResult {
  readonly exitCode: number;
  readonly stdout: string;
  readonly stderr: string;
}

export interface ExecOptions {
  readonly cwd: string;
  readonly encoding: "utf8";
  readonly timeout: number;
  readonly maxBuffer: number;
}

export type ExecFn = (
  file: string,
  args: readonly string[],
  options: ExecOptions,
  callback: (
    error: ExecFileException | null,
    stdout: string,
    stderr: string
  ) => void
) => void;

const defaultExec: ExecFn = (file, args, options, callback) => {
  execFile(file, args, options, callback);
};

export function runCli(
  pythonPath: string,
  cwd: string,
  args: string[],
  timeoutMs = 30000,
  exec: ExecFn = defaultExec
): Promise<CliResult> {
  return new Promise<CliResult>((resolve) => {
    exec(
      pythonPath,
      ["-m", "app.main", ...args],
      { cwd, encoding: "utf8", timeout: timeoutMs, maxBuffer: 10 * 1024 * 1024 },
      (error, stdout, stderr) => {
        const code =
          error && typeof (error as { code?: unknown }).code === "number"
            ? (error as { code: number }).code
            : error
              ? 1
              : 0;
        resolve({ exitCode: code, stdout: stdout ?? "", stderr: stderr ?? "" });
      }
    );
  });
}