// Deterministic presentation layer (Phase 5).
//
// Builds the webview HTML that shows authoritative CLI output verbatim:
//   * every CLI character is HTML-escaped (never interpreted);
//   * the layout is fixed and deterministic (no timestamps, no dynamic
//     styling, no scripts);
//   * empty input renders a stable "no data" notice, never fabricated data.

const CSS = `body{font-family:var(--vscode-editor-font-family);`
  + `font-size:var(--vscode-editor-font-size);padding:1rem;}`
  + `pre{white-space:pre-wrap;word-break:break-all;}`;

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function renderReport(title: string, stdout: string): string {
  const body = stdout.trim() === "" ? NO_DATA_MESSAGE : escapeHtml(stdout);
  return wrap(title, body);
}

export function renderError(title: string, message: string): string {
  return wrap(title, escapeHtml(message));
}

const NO_DATA_MESSAGE = "(no data)";

function wrap(title: string, body: string): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${escapeHtml(title)}</title>
<style>${CSS}</style>
</head>
<body>
<h1>${escapeHtml(title)}</h1>
<pre>${body}</pre>
</body>
</html>`;
}