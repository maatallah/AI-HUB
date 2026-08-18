// Offline-only ambient stub for the NodeJS global namespace used by the
// extension and its unit tests (process, require, __dirname, console).
// Supplied by @types/node in the owner build.

declare namespace NodeJS {
  interface ProcessEnv {
    [key: string]: string | undefined;
  }
  interface Process {
    env: ProcessEnv;
    cwd(): string;
  }
  interface Module {
    exports: unknown;
  }
  interface Require {
    (id: string): unknown;
  }
  interface Timeout {
    unref(): void;
  }
  interface Console {
    log(msg: unknown): void;
  }
}

declare const process: NodeJS.Process;
declare function require(id: string): unknown;
declare const __dirname: string;
declare const module: NodeJS.Module;
declare const exports: unknown;
declare const console: Console;
declare const setInterval: (
  cb: (...args: unknown[]) => void,
  ms: number
) => NodeJS.Timeout;
declare const setTimeout: (
  cb: (...args: unknown[]) => void,
  ms: number
) => NodeJS.Timeout;

interface PromiseLike<T> {}
type Thenable<T> = PromiseLike<T> | Promise<T>;
