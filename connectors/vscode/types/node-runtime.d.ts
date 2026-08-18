// Offline-only ambient stubs for test-runtime builtins (node:test,
// node:assert, node:fs, node:path). Provided by @types/node at owner build.

declare module "node:test" {
  interface TestContext {
    (name: string, fn: () => void | Promise<void>): void;
  }
  const test: TestContext;
  export default test;
}

declare module "node:assert/strict" {
  interface Assert {
    strictEqual<T>(actual: T, expected: T, message?: string): void;
    deepStrictEqual<T>(actual: T, expected: T, message?: string): void;
    ok(value: unknown, message?: string): void;
    throws(fn: () => void, message?: string): void;
    fail(message?: string): void;
  }
  const assert: Assert;
  export = assert;
}

declare module "node:assert" {
  export const strict: import("node:assert/strict");
  const assert: {
    equal<T>(actual: T, expected: T, message?: string): void;
  };
  export { assert as default };
}

declare module "node:fs" {
  export function readFileSync(path: string, encoding: string): string;
}

declare module "node:path" {
  export function join(...parts: string[]): string;
  export function dirname(path: string): string;
  export function resolve(...parts: string[]): string;
}