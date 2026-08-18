// Offline-only ambient type stubs for Node builtins used by the extension,
// allowing offline compile + unit tests with the global `tsc`.

declare module "node:child_process" {
  export interface ExecException extends Error {
    cmd?: string;
    killed?: boolean;
    code?: number | string;
    signal?: string;
    stdout?: string;
    stderr?: string;
  }
  export type ExecFileException =
    & Omit<ExecException, "code">
    & { code?: string | number | null };
  export interface ExecOptions {
    cwd?: string;
    timeout?: number;
    maxBuffer?: number;
    encoding?: string;
    env?: NodeJS.ProcessEnv;
  }
  export function execFile(
    file: string,
    args: readonly string[],
    options: ExecOptions,
    callback: (error: ExecFileException | null, stdout: string, stderr: string) => void
  ): void;
}
