export function nextStep(data: any, base: string): { label: string; href: string } {
  const pending = Array.isArray(data?.pending_approvals) ? data.pending_approvals : [];
  const documents = Array.isArray(data?.documents) ? data.documents : [];
  const recentRuns = Array.isArray(data?.recent_runs) ? data.recent_runs : [];
  const gates = Array.isArray(data?.gates) ? data.gates : [];

  if (pending.length) return { label: `Review: ${pending[0].title || "Pending decision"}`, href: `${base}/runs/${pending[0].run_id}` };
  if (!data?.repo && !documents.length) return { label: "Connect a repository, or write requirements in BA Studio", href: `${base}/repository` };
  if (data?.repo && !recentRuns.some((r: any) => r?.workflow === "bug_scan")) return { label: "Scan the repository for bugs", href: `${base}/bugs` };
  if (!gates.every((g: any) => g?.status === "approved")) return { label: "Continue the QE lifecycle", href: `${base}/qe` };
  return { label: "All gates approved. Review the release document", href: `${base}/documents` };
}
