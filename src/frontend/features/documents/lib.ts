export function getGovernanceId(doc: any, project: any, index: number): string {
  if (doc?.governance_id) return doc.governance_id;
  const rawPrefix = (project?.id || "PRJ").replace(/^prj_/, "").replace(/[^a-zA-Z0-9]/g, "").slice(0, 4).toUpperCase();
  const prefix = rawPrefix || "QE";
  const num = String(index + 1).padStart(3, "0");
  return `${prefix}-DOC-${num}`;
}

export const reopenText = (gates: number[]) => (gates.length > 1 ? `Gates G${gates[0]} to G${gates[gates.length - 1]}` : `Gate G${gates[0]}`);

export function getDocGovernanceId(doc: any, project: any): string {
  if (doc?.governance_id) return doc.governance_id;
  const rawPrefix = (project?.id || "PRJ").replace(/^prj_/, "").replace(/[^a-zA-Z0-9]/g, "").slice(0, 4).toUpperCase();
  const prefix = rawPrefix || "QE";
  return `${prefix}-DOC-${(doc?.id || "001").slice(-3).toUpperCase()}`;
}

export const KIND_LABELS: Record<string, string> = {
                  brd: "BRD",
                  gherkin: "Gherkin",
                  requirements: "Requirements",
                  test_cases: "Test Cases",
                  test_plan: "Test Plan",
                  test_data: "Test Data",
                  discovery: "Discovery",
                  test_code: "Test Code",
                  traceability: "Traceability",
                  release: "Release Sign-off",
                  defect_report: "Defect Report",
};

export function downloadDoc(doc: any) {
  const content = doc.content || `# ${doc.title}\n\nGovernance ID: ${doc.id}\nKind: ${doc.kind}\nStatus: ${doc.status}\n`;
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${doc.title.replace(/[^a-zA-Z0-9_-]/g, "_")}_${doc.id}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
