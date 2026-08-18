// Feature registry for the AI-Hub VS Code extension (Phase 5).
//
// Every feature maps to ONE documented data-access approach: a read-only
// invocation of the AI-Hub CLI (`python -m app.main ...`). The extension
// displays the CLI's authoritative stdout verbatim - it never opens SQLite,
// never parses/recomputes decisions, and never issues a mutating command.
//
// Only read-only CLI actions are used here:
//   - dashboard report <name>        (report builders, read-only)
//   - score list                     (scoring read path)
//   - recommend chain --task X       (build_chain; does NOT record provenance)
//   - fallback status                (build_chain over default task)
//   - dashboard history ...          (event reconstruction, read-only)
// None of these write to the database.

export interface Feature {
  readonly commandId: string;
  readonly title: string;
  readonly requiresInput: "task" | "model_id" | "report" | "none";
  /** Build the `python -m app.main ...` argument list for this feature. */
  readonly buildArgs: (input: string) => string[];
}

const DASHBOARD_REPORTS = [
  "overview",
  "providers",
  "scores",
  "recommendations",
  "monitoring",
] as const;

export const REPORT_NAMES: readonly string[] = DASHBOARD_REPORTS;

export const FEATURES: readonly Feature[] = [
  {
    commandId: "ai-hub.status",
    title: "Provider Status",
    requiresInput: "none",
    buildArgs: () => ["dashboard", "report", "providers"],
  },
  {
    commandId: "ai-hub.modelScores",
    title: "Model Scores",
    requiresInput: "none",
    buildArgs: () => ["score", "list"],
  },
  {
    commandId: "ai-hub.recommendations",
    title: "Recommendations",
    requiresInput: "task",
    buildArgs: (task) => ["recommend", "chain", "--task", task],
  },
  {
    commandId: "ai-hub.fallbackChain",
    title: "Fallback Chain",
    requiresInput: "none",
    buildArgs: () => ["fallback", "status"],
  },
  {
    commandId: "ai-hub.scoreHistory",
    title: "Score History",
    requiresInput: "model_id",
    buildArgs: (modelId) => ["dashboard", "history", "--model", modelId],
  },
  {
    commandId: "ai-hub.availabilityHistory",
    title: "Availability History",
    requiresInput: "none",
    buildArgs: () => ["dashboard", "history", "--availability"],
  },
  {
    commandId: "ai-hub.dashboardReport",
    title: "Dashboard Report",
    requiresInput: "report",
    buildArgs: (name) => ["dashboard", "report", name],
  },
];

export function featureByCommand(commandId: string): Feature {
  const feature = FEATURES.find((f) => f.commandId === commandId);
  if (!feature) {
    throw new Error(`Unknown command id: ${commandId}`);
  }
  return feature;
}

export function isValidReportName(name: string): boolean {
  return (REPORT_NAMES as readonly string[]).includes(name);
}
