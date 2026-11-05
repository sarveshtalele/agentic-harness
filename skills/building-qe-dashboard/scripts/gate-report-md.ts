// Markdown gate reports: one per gate, written next to the documents it approves (docs/qe/<app>/<phase>/gate-<N>-report.md).
// Reports are Markdown only. Guardrail: the Gate 5 report embeds every valid evidence image under 06-execution/evidence/,
// and checkReportImages() names any evidence image a saved report does not show, or any image link that does not resolve.
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, posix, relative } from "node:path";
import { PHASES, GATE_PHASES, EVIDENCE_DIR, findDoc, readJsonDoc, docItems } from "../../../hooks/src/layout.ts";
import { GATE_NAMES, gateStatus, type GateState } from "../../../hooks/src/on-decision.ts";
import { safeWrite, localIso } from "../../../hooks/src/hook-common.ts";
import { collectTrace, frId, norm, overall, lowConfidencePasses, type TraceInput } from "./build-trace-report.ts";
import { RUBRIC, THRESHOLD, ASSERTION_FLOOR, type Kind } from "../../../hooks/src/confidence.ts";

export const MAX_EVIDENCE_IMAGE = 5 * 1024 * 1024;
const VERSION = (() => { try { return String(JSON.parse(readFileSync(new URL("../../../.claude-plugin/plugin.json", import.meta.url), "utf-8")).version); } catch { return ""; } })();
const GATE_CMD = ["qe-start", "qe-requirements", "qe-plan", "qe-design", "qe-generate", "qe-sign"];
const NEXT_CMD = ["qe-discover", "qe-plan", "qe-design", "qe-generate", "qe-execute", null];

/** Folder (relative to docs/qe/<app>/) that holds a gate's report: the last phase the gate approves. */
export function gateReportRel(gate: number): string {
  const ids = GATE_PHASES[gate] ?? [];
  const dir = PHASES.find((p) => p.id === ids[ids.length - 1])?.dir ?? "00-intake";
  return `${dir}/gate-${gate}-report.md`;
}

const imageKind = (f: string): "png" | "jpg" | null => {
  try {
    if (statSync(f).size > MAX_EVIDENCE_IMAGE) return null;
    const b = readFileSync(f).subarray(0, 4);
    return b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47 ? "png" : b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff ? "jpg" : null;
  } catch { return null; }
};

/** Evidence images under 06-execution/evidence/ (paths relative to the app folder): valid ones, and the ones that cannot be shown and why. */
export function evidenceImages(appDir: string): { valid: string[]; invalid: { path: string; reason: string }[] } {
  const valid: string[] = [], invalid: { path: string; reason: string }[] = [];
  const walk = (rel: string, depth: number) => {
    let es: import("node:fs").Dirent[] = [];
    try { es = readdirSync(join(appDir, rel), { withFileTypes: true }); } catch { return; }
    for (const e of es.sort((a, b) => a.name.localeCompare(b.name))) {
      const r = `${rel}/${e.name}`;
      if (e.isSymbolicLink()) continue;
      if (e.isDirectory() && depth < 4) walk(r, depth + 1);
      else if (e.isFile() && /\.(png|jpe?g)$/i.test(e.name)) {
        const k = imageKind(join(appDir, r));
        if (k && (k === "png") === /\.png$/i.test(e.name)) valid.push(r);
        else invalid.push({ path: r, reason: statSync(join(appDir, r)).size > MAX_EVIDENCE_IMAGE ? "larger than 5 MB" : "not a PNG or JPEG file" });
      }
    }
  };
  walk(EVIDENCE_DIR, 0);
  return { valid, invalid };
}

/** Guardrail: evidence images a report does not embed, and embedded images that do not exist (paths relative to the app folder). */
export function checkReportImages(appDir: string, reportRel: string, md: string): { missing: string[]; broken: string[] } {
  const dir = posix.dirname(reportRel);
  // a malformed link (bad %-escape) is a broken image, never an exception (AQE140-008)
  const dec = (u: string): string | null => { try { return decodeURI(u); } catch { return null; } };
  const raw = [...md.matchAll(/!\[[^\]]*\]\(([^)\s]+)\)/g)].map((m) => m[1]);
  const linked = raw.map((u) => { const d = dec(u); return d === null ? `(malformed) ${u}` : posix.normalize(posix.join(dir, d)); });
  const { valid } = evidenceImages(appDir);
  return { missing: valid.filter((v) => !linked.includes(v)), broken: linked.filter((l) => l.startsWith("(malformed)") || l.startsWith("../") || !existsSync(join(appDir, l)) || !imageKind(join(appDir, l))) };
}

const cell = (v: unknown): string => String(v ?? "").replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>");
const table = (head: string[], rows: unknown[][]): string[] => rows.length ? [`| ${head.join(" | ")} |`, `|${head.map(() => "---").join("|")}|`, ...rows.map((r) => `| ${r.map(cell).join(" | ")} |`), ""] : ["*None.*", ""];
const count = <T>(xs: T[], key: (x: T) => string | undefined) => Object.entries(xs.reduce<Record<string, number>>((a, x) => { const k = key(x) || "unspecified"; a[k] = (a[k] ?? 0) + 1; return a; }, {})).sort();
const STATUS_ICON: Record<GateState, string> = { APPROVED: "✅ APPROVED", REJECTED: "⛔ REJECTED", REOPENED: "⚠️ REOPENED", PENDING: "⏳ PENDING" };

/** The per-case scores of the independent review: every case with its component, then each flaw with its fix. */
function confidenceSection(t: TraceInput, kind: Kind): string[] {
  const sum = t.confidenceSummary[kind];
  const title = kind === "design" ? "### Confidence: designs against the repository" : "### Confidence: generated tests against the repository";
  if (!sum) return [title, "", "*Not reviewed yet. The `confidence-reviewer` agent scores every case; nothing here is verified until it has.*", ""];
  const items = [...t.confidence.values()].map((c) => c[kind]).filter((i): i is NonNullable<typeof i> => !!i);
  const dims = Object.keys(RUBRIC[kind]);
  const L = [title, "", `Reviewed by the independent \`confidence-reviewer\` agent, which never writes code. ${sum.count} cases: **${sum.approved} APPROVED, ${sum.revise} REVISE, ${sum.reject} REJECT**; average ${sum.average}/100; ${sum.low} low confidence (REJECT, under ${THRESHOLD}${kind === "code" ? `, or assertion integrity under ${ASSERTION_FLOOR}` : ""}).`, ""];
  if (sum.stamp) L.push(`Evidence: ${sum.stamp}.`, "");
  else L.push(`Evidence: ${sum.evidence.verified} verified in this folder, ${sum.evidence["not-checked"]} not checked, ${sum.evidence.missing} not found.`, "");
  L.push(...table(["Case", "Component", ...dims.map((d) => `${d.replace(/_/g, " ")} /${RUBRIC[kind][d]}`), "Total", "Verdict"], items.map((i) => [i.tc_id, i.component?.file ? `\`${i.component.file}${i.component.line ? `:${i.component.line}` : ""}\`${i.component.symbol ? ` ${i.component.symbol}` : ""}` : "", ...dims.map((d) => i.scores[d] ?? ""), i.total, i.effective])));
  const lowItems = items.filter((i) => i.low);
  if (lowItems.length) L.push(`#### Low confidence (${lowItems.length}): a pass on these is not counted as verified`, "", ...table(["Case", "Why"], lowItems.map((i) => [i.tc_id, i.lowReason])));
  const weak = items.filter((i) => i.effective !== "APPROVED");
  if (weak.length) {
    L.push(`#### Flaws to fix (${weak.length})`, "");
    L.push(...table(["Case", "Verdict", "Dimension", "Evidence", "Fix"], weak.flatMap((i) => [...(i.flaws ?? []).map((f) => [i.tc_id, i.effective, f.dimension, `\`${f.evidence}\``, f.fix]), ...i.problems.map((p) => [i.tc_id, i.effective, "record", "", p])])));
  }
  return L;
}

/** The Markdown report for one gate. `gates` defaults to the project's ledger (pass another for a copied example). */
export function gateReportMd(root: string, app: string, gate: number, opts: { gates?: Record<number, { status: GateState; timestamp?: string }>; now?: string } = {}): string {
  const appDir = join(root, "docs", "qe", app);
  const t = collectTrace(root, app);
  const gs = (opts.gates ?? gateStatus(join(root, ".qe")))[gate] ?? { status: "PENDING" as GateState };
  const rel = gateReportRel(gate), up = (p: string) => posix.relative(posix.dirname(rel), p);
  const phases = (GATE_PHASES[gate] ?? []).map((id) => PHASES.find((p) => p.id === id)!).filter(Boolean);
  const L: string[] = [
    "---", `doc_id: ${rel.replace(/\.md$/, "")}`, `created_at: ${opts.now ?? localIso()}`, `created_by: agentic-qe${VERSION ? ` v${VERSION}` : ""}`, `mode: ${t.mode}`, `source_commit: ${t.commit}`, "---", "",
    `# Gate ${gate} report: ${GATE_NAMES[gate]} (${app})`, "",
    ...table(["Field", "Value"], [["Status", STATUS_ICON[gs.status]], ["Decided at", gs.timestamp ?? "not decided yet"], ["Approves", phases.map((p) => p.title).join(", ")], ["Approval phrase", `\`${gate === 0 ? `approve gate 0 for ${app}` : `approve gate ${gate}`}\``]]),
    "## Documents in this gate", ""
  ];
  const docs: unknown[][] = [];
  for (const p of phases) for (const k of Object.keys(p.docs)) {
    const f = findDoc(appDir, `${p.id}.${k}`);
    if (!existsSync(f)) continue;
    const r = relative(appDir, f).replace(/\\/g, "/"), s = statSync(f);
    docs.push([p.title, `[${r}](${up(r)})`, `${(s.size / 1024).toFixed(1)} KB`, new Date(s.mtimeMs).toISOString().slice(0, 16).replace("T", " ")]);
  }
  L.push(...table(["Phase", "Document", "Size", "Updated (UTC)"], docs), "## Summary", "");

  if (gate === 0) L.push(...table(["Field", "Value"], [["Application", app], ["Mode", t.mode], ["Scope", t.scope || "not stated"], ["Frameworks", t.frameworks.join(", ") || "none detected"], ["Source commit", t.commit]]));
  if (gate === 1) {
    L.push(`${t.requirements.length} requirements and ${t.stories.length} user stories.`, "");
    L.push(...table(["Control ID", "Requirement", "Priority", "Evidence"], t.requirements.map((r) => [frId(r.id), r.text || r.title, r.priority, r.evidence])));
  }
  if (gate === 2) L.push(...table(["Level", "Plan"], Object.entries(t.levels)));
  if (gate === 3) {
    L.push(`${t.cases.length} designed test cases.`, "", "### By level", "", ...table(["Level", "Cases"], count(t.cases, (c) => c.level)), "### By type", "", ...table(["Type", "Cases"], count(t.cases, (c) => c.type)), "### By priority", "", ...table(["Priority", "Cases"], count(t.cases, (c) => c.priority)), ...confidenceSection(t, "design"));
  }
  if (gate === 4) {
    const files = [...t.generated.entries()];
    L.push(`${files.reduce((n, [, f]) => n + f.length, 0)} generated test files for ${files.length} cases.`, "", ...table(["Case", "Files"], files.map(([id, f]) => [id, f.map((x) => `\`${x}\``).join("<br>")])), ...confidenceSection(t, "code"));
  }
  if (gate === 5) {
    const v = overall(t);
    L.push(`**Verdict: ${v.verdict}.** ${v.reason}`, "", "### Results", "", ...table(["Run", "Total", "Passed", "Failed", "Skipped", "Status"], t.execRuns.map((r) => [r.label || r.file, r.total, r.passed, r.failed, r.skipped, r.status])));
    const defects = [...t.healer.values()].filter((d) => /APPLICATION_DEFECT/i.test(d.classification));
    L.push("### Defects: why the tests failed and how to fix them", "");
    if (!defects.length) L.push("*No application defects.*", "");
    for (const d of defects) {
      const c = t.cases.find((x) => norm(x.tc_id) === norm(d.tc_id));
      L.push(`#### ${d.tc_id}${c?.scenario ? `: ${c.scenario}` : ""}${d.severity ? ` (${d.severity})` : ""}`, "", ...table(["", ""], [["Requirement", c?.story_id ? frId(c.story_id) : ""], ["Why it failed", t.runs.get(norm(d.tc_id))?.message?.split("\n")[0] ?? d.evidence], ["Root cause", d.detail], ["How to fix", d.fix], ["Test file", d.file ? `\`${d.file}\`` : ""]].filter((r) => r[1])));
    }
    const heals = docItems(readJsonDoc(findDoc(appDir, "healing.log")), "heals");
    if (heals.length) L.push("### Test drift healed (no assertion weakened)", "", ...table(["Cases", "Class", "Change"], heals.map((h: any) => [[].concat(h.tc_ids ?? h.tc_id ?? []).join(", "), h.classification, h.change])));
    const lowPass = lowConfidencePasses(t);
    const ds = t.confidenceSummary.design, cs = t.confidenceSummary.code;
    L.push("### Confidence", "", ds || cs ? `Designs: ${ds ? `average ${ds.average}/100, ${ds.low} low confidence` : "not reviewed"}. Generated tests: ${cs ? `average ${cs.average}/100, ${cs.low} low confidence` : "not reviewed"}.` : "*Not reviewed: a pass here has no independent check behind it.*", "");
    if (lowPass.length) L.push(`**Passed with low confidence, so not counted as verified:** ${lowPass.join(", ")}. See the Gate 3 and Gate 4 reports for why.`, "");
    const cov = [...t.covered.values()];
    L.push("### Traceability", "", `${t.requirements.length} requirements; ${cov.filter(Boolean).length} of ${cov.length} traced cases covered.`, "");
    const ev = evidenceImages(appDir);
    L.push("### Screenshots", "");
    if (!ev.valid.length) L.push("*No screenshots in `06-execution/evidence/`. Run `collect-evidence.ts` after the UI suite.*", "");
    for (const img of ev.valid) L.push(`![${posix.basename(img).replace(/\.(png|jpe?g)$/i, "")}](${encodeURI(up(img))})`, "");
    if (ev.invalid.length) L.push("Images that cannot be shown:", "", ...table(["File", "Reason"], ev.invalid.map((i) => [i.path, i.reason])));
  }
  L.push("## Next step", "");
  if (gs.status !== "APPROVED") L.push(`Review the documents above, then type \`${gate === 0 ? `approve gate 0 for ${app}` : `approve gate ${gate}`}\` in your agent session.`, "");
  else if (NEXT_CMD[gate]) L.push(`Run \`/agentic-qe:${NEXT_CMD[gate]} ${app}\`.`, "");
  else L.push("The run is signed off.", "");
  L.push(`*The documents in this gate are produced by \`/agentic-qe:${GATE_CMD[gate]} ${app}\`.*`, "");
  return L.join("\n");
}

/** Writes the gate report next to its documents (inside root). Returns its path relative to the app folder. */
export function writeGateReport(root: string, app: string, gate: number): string {
  const rel = gateReportRel(gate);
  safeWrite(join(root, "docs", "qe", app, rel), gateReportMd(root, app, gate), root);
  return rel;
}
