// Values the pane keeps in $.state (claude plugin validate holds hooks/pane.tsx to this contract).
export type PaneCase = { id: string; level: string; status: string; low: boolean };
export type PaneCounts = { passed: number; failed: number; total: number };
export type PaneData = {
  app: string | null;
  apps: string[];
  mode: string | null;
  hasRun: boolean;
  phases: { id: string; label: string; done: boolean; active: boolean; outOfOrder: boolean }[];
  gates: string[];
  levels: Record<string, PaneCounts>;
  blockers: string[];
  ledger: { ok: boolean; reason?: string };
  next: string;
  approval: string | null;
  reject: string | null;
  pendingGate: number | null;
  gateReport: string | null;
  dashboard: string | null;
  cases: PaneCase[];
  low: number;
  confidence: number | null;
  coverage?: { gate: number; ok: boolean; gaps: string[]; more: number; counts: Record<string, number> } | null;
  inventory?: { files: number; tests: number; existing: number; generated: number; manual: number; byLevel: Record<string, number> } | null;
  toGenerate?: number;
  validation?: { gate: number; ok: boolean; errors: number; warnings: number; first?: string; error?: string } | null;
  version?: string;
};
export type PaneActivity = { tool: string | null; count: number; turnId: string | null };

declare module "claude-code" {
  interface PluginState {
    "agentic-qe": {
      data: Shaped<PaneData | null>;
      view: "auto" | "open" | "hidden";
      placed: boolean;
      dialog: boolean;
      app: string | null;
      exported: string;
      activity: Shaped<PaneActivity>;
    };
  }
}
