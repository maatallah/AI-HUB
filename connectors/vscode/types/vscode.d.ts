// Offline-only ambient type stubs so the extension compiles and unit-tests
// with the global `tsc` without requiring `npm install`. In the real build
// the host-provided `vscode` module supplies these at runtime.

declare module "vscode" {
  export interface Disposable {
    dispose(): void;
  }
  export class Disposable {
    constructor(callOnDispose?: () => void);
    static from(...disposables: Disposable[]): Disposable;
    dispose(): void;
  }

  export interface Uri {
    scheme: string;
    authority: string;
    path: string;
    fsPath: string;
    toString(skipEncoding?: boolean): string;
  }
  export namespace Uri {
    function file(path: string): Uri;
    function parse(value: string): Uri;
  }

  export enum ViewColumn {
    Active = -1,
    Beside = -2,
    One = 1,
    Two = 2,
    Three = 3,
  }

  export interface Webview {
    html: string;
    options: { enableScripts: boolean };
    onDidReceiveMessage(cb: (msg: unknown) => void): Disposable;
  }

  export interface WebviewPanel {
    readonly webview: Webview;
    readonly viewType: string;
    title: string;
    onDidDispose(cb: () => void): Disposable;
    dispose(): void;
  }

  export interface WebviewPanelOptions {
    enableScripts?: boolean;
  }

  export interface TreeItem {
    label: string;
    description?: string;
    collapsibleState?: number;
    command?: { command: string; title: string; arguments?: unknown[] };
    iconPath?: Uri;
  }
  export class TreeItem {
    constructor(label: string, collapsibleState?: number);
    label: string;
    description?: string;
    collapsibleState?: number;
    command?: { command: string; title: string; arguments?: unknown[] };
    iconPath?: Uri;
  }

  export interface TreeDataProvider<T> {
    getChildren(element?: T): T[] | Thenable<T[]>;
    getTreeItem(element: T): TreeItem | Thenable<TreeItem>;
  }

  export interface TreeView<T> {
    dispose(): void;
  }

  export interface Configuration {
    get<T>(section: string, defaultValue?: T): T | undefined;
  }

  export interface WorkspaceFolder {
    uri: Uri;
    name: string;
  }

  export interface MessageItem {
    title: string;
  }

  export interface QuickPickItem {
    label: string;
    description?: string;
    detail?: string;
  }

  export interface ExtensionContext {
    subscriptions: Disposable[];
    extensionUri: Uri;
    workspaceState: Memento;
    globalState: Memento;
  }

  export interface Memento {
    get<T>(key: string, defaultValue?: T): T | undefined;
    update(key: string, value: unknown): Thenable<void>;
  }

  export namespace commands {
    function registerCommand(
      command: string,
      callback: (...args: unknown[]) => unknown,
      thisArg?: unknown
    ): Disposable;
    function executeCommand<T>(command: string, ...rest: unknown[]): Thenable<T | undefined>;
  }

  export namespace window {
    function createWebviewPanel(
      viewType: string,
      title: string,
      column: ViewColumn,
      options: WebviewPanelOptions
    ): WebviewPanel;
    function showErrorMessage(message: string, ...items: string[]): Thenable<string | undefined>;
    function showInformationMessage(
      message: string,
      ...items: string[]
    ): Thenable<string | undefined>;
    function showInputBox(options: {
      prompt?: string;
      placeHolder?: string;
      value?: string;
      validateInput?: (value: string) => string | undefined;
    }): Thenable<string | undefined>;
    function showQuickPick<T extends QuickPickItem>(
      items: readonly T[] | Thenable<readonly T[]>,
      options?: { placeHolder?: string; canPickMany?: boolean }
    ): Thenable<T | undefined>;
    function createTreeView<T>(
      viewId: string,
      options: { treeDataProvider: TreeDataProvider<T> }
    ): TreeView<T>;
  }

  export namespace workspace {
    function getConfiguration(section?: string): Configuration;
    function getConfiguration(section: string, resource: Uri): Configuration;
    const workspaceFolders: readonly WorkspaceFolder[] | undefined;
  }
}
