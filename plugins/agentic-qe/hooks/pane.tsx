// The QE pane beside the transcript: a Claude Code mod (https://code.claude.com/docs/en/plugins/mods/overview).
// Mods load by default on Claude Code 2.1.287 or later (Desktop 2.1.286); an older build refuses this module and the
// plugin's command hooks keep working. Every fact comes from `panel.ts --json`, the same reading as the terminal panel.
// It records nothing and runs no command by itself: its buttons put a command or an approval phrase in the prompt box,
// and a person presses Enter. The approval hook then records it, as for any typed prompt.
import { atom, read, update } from "claude-code";
import type { EngineInterface, Register } from "claude-code";

import type { PaneActivity, PaneCase, PaneData } from "../types";

const PANE = "agentic-qe";
const TITLE = "Agentic QE";
const WATCH_FLAG = /^\s*\/(?:agentic-qe:)?qe-panel\b.*--(?:watch|split)\b/;
const GATE_NAMES = ["Intake", "Requirements", "Plan", "Design", "Generate", "Release"];
/** The next command stands out in light blue. */
const NEXT_COLOR = "#5fb4ff";
const WRITING = new Set(["Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"]);

const data = atom({ plugin: "agentic-qe", key: "data" } as const, null, { shape: "qe-pane-3" });
const view = atom({ plugin: "agentic-qe", key: "view" } as const, "auto");
const placed = atom({ plugin: "agentic-qe", key: "placed" } as const, true);
const dialog = atom({ plugin: "agentic-qe", key: "dialog" } as const, false);
const app = atom({ plugin: "agentic-qe", key: "app" } as const, null);
const exported = atom({ plugin: "agentic-qe", key: "exported" } as const, "");
const activity = atom({ plugin: "agentic-qe", key: "activity" } as const, { tool: null, count: 0, turnId: null } as PaneActivity, { shape: "qe-activity-2" });

/** One tile: red fails, yellow passes without an independent check behind them, green passes, dim not run. */
const tileColor = (c: PaneCase): string | undefined => (c.status === "FAIL" ? "error" : c.status !== "PASS" ? undefined : c.low ? "warning" : "success");

/** `panel` option: auto opens by itself and keeps the show bar; command opens only when asked; off draws nothing. */
let mode = "auto";

async function load($: EngineInterface): Promise<void> {
  const chosen = await read($, app);
  const argv = ["node", `${$.plugin.root}/skills/qe-panel/scripts/panel.ts`, "--json", "--root", await $.session.cwd()];
  const r = await $.process.run(chosen ? [...argv, "--app", chosen] : argv, { timeoutMs: 15000 });
  if (r.exitCode === 0) await update($, data, () => JSON.parse(r.stdout) as PaneData);
}
async function show($: EngineInterface) {
  await update($, view, () => "open");
  await load($).catch(() => undefined);
  const r = await $.ui.open({ id: PANE, title: TITLE });
  await update($, placed, () => r.isPlaced);
}
async function hide($: EngineInterface) {
  await update($, view, () => "hidden");
  await update($, dialog, () => false);
  await $.ui.close({ id: PANE });
}
/** Puts text in the prompt box. Never submits it. */
async function fill($: EngineInterface, text: string) {
  await update($, dialog, () => false);
  await $.prompt.fill({ text });
}
async function nextApp($: EngineInterface) {
  const d = await read($, data);
  if (!d || d.apps.length < 2) return;
  const i = d.apps.indexOf(d.app ?? "");
  await update($, app, () => d.apps[(i + 1) % d.apps.length]);
  await load($).catch(() => undefined);
}
/** Writes the plugin's record of the run to docs/qe/<app>/sessions/ (the user pressed the button or typed /qe-pane export). */
async function exportRun($: EngineInterface): Promise<string> {
  const d = await read($, data);
  if (!d?.app) return "no run to export";
  const r = await $.process.run(["node", `${$.plugin.root}/skills/qe-panel/scripts/export-session.ts`, "--root", await $.session.cwd(), "--app", d.app], { timeoutMs: 20000 });
  const msg = r.exitCode === 0 ? r.stdout.trim() : `export failed: ${(r.stderr || "").trim().slice(0, 200)}`;
  await update($, exported, () => msg);
  return msg;
}
async function stopRun($: EngineInterface) {
  const a = await read($, activity);
  if (a.turnId) await $.turn.abort({ turnId: a.turnId });
}

let waiting = false;
/** A burst of tool calls reads the files once. */
const soon = ($: EngineInterface) => {
  if (waiting) return;
  waiting = true;
  $.clock.after(800, () => { waiting = false; void load($).catch(() => undefined); });
};

export const register: Register = (on, options) => {
  mode = options.panel === "command" || options.panel === "off" ? String(options.panel) : "auto";

  on("session.start", async ($, e, next) => {
    const started = await next(e);
    await $.command.register({ name: "qe-pane", description: "Show or hide the live QE pane beside the transcript: open, close or json", immediate: true });
    await load($).catch(() => undefined);
    // opens by itself once a run exists, unless the panel option says otherwise; a person who hid it keeps it hidden
    const was = await read($, view);
    if (mode !== "off" && (was === "open" || (mode === "auto" && was === "auto" && (await read($, data))?.hasRun))) void show($).catch(() => undefined);
    // no refresh button: files are read after writes, when a watched file changes (FileChanged), when a turn ends, and every 5 seconds
    $.clock.every(5000, () => void load($).catch(() => undefined));
    return started;
  });

  // /clear, /resume and /branch reset $.state without a new session.start: read the files again
  on("classic.SessionStart", { source: ["clear", "resume", "fork"] }, async ($, e, next) => {
    await load($).catch(() => undefined);
    return next(e);
  }).catch(($, e, next) => next(e)); // an observer: if it fails, the event goes on unchanged

  on("command.run", { command: "qe-pane" }, async ($, e) => {
    const arg = e.args.trim().toLowerCase();
    if (arg === "json") {
      await load($).catch(() => undefined);
      return { text: JSON.stringify(await read($, data), null, 1) };
    }
    if (arg === "export") return { text: await exportRun($) };
    const isOpen = (await read($, view)) === "open";
    if (arg === "close" || (arg !== "open" && isOpen)) { await hide($); return { text: "QE pane hidden. /qe-pane brings it back." }; }
    await show($);
    return { text: (await read($, placed)) ? "QE pane shown." : "QE pane is waiting for a wider terminal; the row above the prompt has show pane." };
  });

  // --watch and --split open the pane here, in place of a second terminal
  on("prompt.submit", async ($, e, next) => {
    await update($, activity, (a) => ({ ...a, count: 0 }));
    if (mode === "off" || !WATCH_FLAG.test(e.text)) return next(e);
    await show($);
    const note = (await read($, placed))
      ? "The live QE pane is open beside the transcript. Start no terminal watcher, no split and no dashboard; say so in one line."
      : "The live QE pane is ready but waits for a wider terminal; the row above the prompt has a show pane button, and /qe-pane opens it at any width. Start no terminal watcher, no split and no dashboard; tell the user this in one line.";
    return next({ ...e, context: [...(e.context ?? []), note] });
  }).catch(($, e, next) => next(e)); // an observer: if it fails, the event goes on unchanged

  // a watched file changed outside Claude's tools (your editor, git): read the files again at once
  on("classic.FileChanged", async ($, e, next) => {
    soon($);
    return next(e);
  }).catch(($, e, next) => next(e));

  on("turn.start", async ($, e, next) => {
    await update($, activity, (a) => ({ ...a, turnId: e.turnId }));
    return next(e);
  }).catch(($, e, next) => next(e));

  on("tool.call", async ($, e, next) => {
    await update($, activity, (a) => ({ ...a, tool: e.tool, count: a.count + 1 }));
    const ran = await next(e);
    if (WRITING.has(e.tool)) soon($);
    return ran;
  }).catch(($, e, next) => next(e)); // an observer: if it fails, the event goes on unchanged

  on("turn.complete", async ($, e, next) => {
    await update($, activity, (a) => ({ ...a, tool: null, turnId: null }));
    soon($);
    return next(e);
  });

  on("ui.render", { component: "Pane", requestId: PANE }, async ($, e) => {
    const { Box, Button, Text } = $.ui.resolve(e);
    const d = await read($, data), act = await read($, activity), asking = await read($, dialog);
    if (!d?.app) {
      return (
        <Box flexDirection="column">
          <Text dimColor>No QE run in this folder.</Text>
          <Text>Start one with /agentic-qe:qe-start &lt;app&gt;</Text>
          <Box>
            <Button key="start" label="put qe-start in prompt" onPress={() => fill($, "/agentic-qe:qe-start ")} />
            <Button key="hide" label="hide" onPress={() => hide($)} />
          </Box>
        </Box>
      );
    }
    const g = d.pendingGate;
    const blocked = !!(d.coverage && !d.coverage.ok && d.coverage.gate === g);
    if (asking && g !== null && d.approval && d.reject) {
      return (
        <Box flexDirection="column">
          <Text bold>Gate {g} {GATE_NAMES[g]}: your decision</Text>
          <Text>Read the gate report before you decide:</Text>
          <Text color="claude">{d.gateReport ?? `docs/qe/${d.app}/ (no report written yet)`}</Text>
          {!d.ledger.ok && <Text color="error">The ledger is not trusted, so a decision is not recorded: {d.ledger.reason ?? ""}</Text>}
          {blocked && <Text color="error">Coverage check fails, so the plugin will not record an approval:</Text>}
          {blocked && d.coverage!.gaps.map((x) => <Text color="warning">! {x}</Text>)}
          {blocked && d.coverage!.more > 0 && <Text dimColor>and {d.coverage!.more} more in docs/qe/{d.app}/coverage-map.md</Text>}
          <Text dimColor>Each button puts the phrase in your prompt. Nothing is recorded until you press Enter.</Text>
          <Box>
            {blocked
              ? <Button key="waive" label="approve with gaps (add your reason)" onPress={() => fill($, `approve gate ${g} with gaps: `)} />
              : <Button key="approve" label={`approve gate ${g}`} onPress={() => fill($, d.approval!)} />}
            <Button key="reject" label={`reject gate ${g}`} onPress={() => fill($, `${d.reject} `)} />
            <Button key="cancel" label="cancel" onPress={() => update($, dialog, () => false)} />
          </Box>
        </Box>
      );
    }
    const levels = [...new Set(d.cases.map((c) => c.level))];
    const finished = d.next === "all phases complete";
    const n = d.coverage?.counts, inv = d.inventory;
    const passed = d.cases.filter((c) => c.status === "PASS").length, failed = d.cases.filter((c) => c.status === "FAIL").length;
    const approved = d.gates.filter((x) => x === "approved").length;
    // a tile: the number large, its name under it, as on the dashboard
    const tile = (key: string, label: string, value: string | number, color?: string) => (
      <Box key={key} flexDirection="column" borderStyle="round" borderDimColor paddingX={1} minWidth={13}>
        <Text bold color={color}>{String(value)}</Text>
        <Text dimColor>{label}</Text>
      </Box>
    );
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- an element tree from this surface's table
    const section = (title: string, body: any, extra?: string) => (
      <Box flexDirection="column" borderStyle="round" borderDimColor paddingX={1} marginTop={0}>
        <Text bold>{title}{extra ? <Text dimColor bold={false}>  {extra}</Text> : ""}</Text>
        {body}
      </Box>
    );
    return (
      <Box flexDirection="column">
        <Box justifyContent="space-between" borderStyle="round" borderColor={NEXT_COLOR} paddingX={1}>
          <Text bold>Agentic QE <Text color={NEXT_COLOR}>· {d.app}</Text>{d.mode ? <Text dimColor bold={false}> · {d.mode}</Text> : ""}{d.version ? <Text dimColor bold={false}> · v{d.version}</Text> : ""}</Text>
          <Box columnGap={1}>
            {d.apps.length > 1 && <Button key="app" label={`app ${d.apps.indexOf(d.app) + 1}/${d.apps.length}`} onPress={() => nextApp($)} />}
            <Button key="hide" label="hide" onPress={() => hide($)} />
          </Box>
        </Box>
        {!d.ledger.ok && <Text color="error">Ledger not trusted, gates read as pending: {d.ledger.reason ?? "no reason recorded"}</Text>}
        {section("Progress", <Text wrap="wrap">{d.phases.map((p) => <Text color={p.done ? "success" : undefined} dimColor={!p.done && !p.active} bold={p.active}>{p.done ? "✓" : p.active ? "▸" : "·"} {p.label.toLowerCase()}  </Text>)}</Text>)}
        {section(`Gates ${approved}/6`, <Text wrap="wrap">{d.gates.map((x, i) => <Text color={x === "approved" ? "success" : x === "rejected" ? "error" : undefined} dimColor={x === "pending"}>{x === "approved" ? "✓" : x === "rejected" ? "✗" : "○"} {i} {GATE_NAMES[i]}   </Text>)}</Text>)}
        {section("Coverage", (
          <Box flexDirection="column">
            <Box flexDirection="row" flexWrap="wrap" columnGap={1}>
              {tile("t-req", "requirements", n?.requirements ?? "-")}
              {tile("t-sc", "plan scenarios", n?.scenarios ?? "-")}
              {tile("t-cases", "designed cases", n?.cases ?? d.cases.length)}
              {tile("t-gen", "to generate", d.toGenerate ?? "-", d.toGenerate ? "warning" : "success")}
              {tile("t-files", "test files", n?.tests ?? "-")}
              {tile("t-repo", "tests in repo", inv ? inv.tests : "-")}
              {tile("t-run", "executed", n?.results ?? "-")}
              {tile("t-pass", "passed", passed, "success")}
              {tile("t-fail", "failed", failed, failed ? "error" : undefined)}
              {d.confidence !== null && tile("t-conf", "confidence", d.confidence, d.low ? "warning" : "success")}
            </Box>
            {inv && <Text dimColor>in the repo: {inv.files} test files · existing {inv.existing} · generated {inv.generated} · added by hand {inv.manual}</Text>}
            {d.coverage && <Text color={d.coverage.ok ? "success" : "error"}>{d.coverage.ok ? `✓ Gate ${d.coverage.gate} coverage check passes` : `✗ Gate ${d.coverage.gate} cannot be approved yet: ${d.coverage.gaps.length + d.coverage.more} gap(s)`}</Text>}
            {d.coverage && !d.coverage.ok && d.coverage.gaps.slice(0, 2).map((x) => <Text color="warning">! {x}</Text>)}
            {d.validation && <Text color={d.validation.ok ? "success" : "error"}>{d.validation.error ? `✗ validator: ${d.validation.error}` : `${d.validation.ok ? "✓" : "✗"} pandas/numpy validator, gate ${d.validation.gate}: ${d.validation.ok ? "PASS" : "FAIL"} · ${d.validation.errors} errors · ${d.validation.warnings} warnings`}</Text>}
            {d.validation && !d.validation.ok && d.validation.first && <Text color="warning">! {d.validation.first}</Text>}
          </Box>
        ))}
        {d.cases.length > 0 && section(`Test cases ${d.cases.length}${d.confidence !== null ? ` · confidence ${d.confidence}` : ""}${d.low ? ` · ${d.low} low` : ""}`, (
          <Box flexDirection="column">
            {levels.map((l) => <Text>{l.padEnd(12)}{d.cases.filter((c) => c.level === l).map((c) => <Text color={tileColor(c)} dimColor={c.status === "NOT RUN"}>■</Text>)}</Text>)}
            <Text><Text color="success">■ pass </Text><Text color="warning">■ low confidence </Text><Text color="error">■ fail </Text><Text dimColor>■ not run</Text></Text>
          </Box>
        ))}
        {section(g !== null ? `Waiting for you: Gate ${g} ${GATE_NAMES[g]}` : "Next", (
          <Box flexDirection="column">
            {g === null && <Text color={NEXT_COLOR}>{d.next}</Text>}
            <Box columnGap={1} flexWrap="wrap">
              {g !== null && <Button key="review" label={`review gate ${g}`} onPress={() => update($, dialog, () => true)} />}
              {g === null && !finished && <Button key="fill" label="put in prompt" onPress={() => fill($, d.next)} />}
              {act.turnId && <Button key="stop" label="stop the run" onPress={() => stopRun($)} />}
            </Box>
          </Box>
        ))}
        {d.blockers.length > 0 && section(`Attention ${d.blockers.length}`, <Box flexDirection="column">{d.blockers.slice(0, 6).map((b) => <Text color="warning">! {b}</Text>)}</Box>)}
        <Box columnGap={1} flexWrap="wrap">
          {d.dashboard
            ? <Button key="link" label="dashboard link" onPress={() => fill($, "/agentic-qe:qe-panel --serve --link")} />
            : <Button key="dashboard" label="start dashboard" onPress={() => fill($, "/agentic-qe:qe-panel --serve")} />}
          <Button key="export" label="export snapshot" onPress={() => fill($, "/agentic-qe:qe-panel --export")} />
          <Button key="session" label="export session" onPress={() => exportRun($)} />
        </Box>
        {d.dashboard && <Text dimColor>Dashboard {d.dashboard}</Text>}
        {(await read($, exported)) && <Text color="success">Session saved: {await read($, exported)}</Text>}
        <Text dimColor>Session {act.tool ? `● ${act.tool}` : act.turnId ? "● working" : "○ idle"}{act.count ? ` · ${act.count} calls` : ""}</Text>
      </Box>
    );
  });

  // one row above the prompt whenever the pane is not on screen: hidden, or waiting for a wider terminal
  on("ui.render", { component: "AbovePrompt" }, async ($, e, next) => {
    const d = await read($, data);
    const off = (await read($, view)) === "hidden" || !(await read($, placed));
    if (mode !== "auto" || !d?.hasRun || !off) return next(e);
    const { Box, Button, Text } = $.ui.resolve(e);
    return (
      <Box>
        <Text dimColor>QE {d.app}: {d.gates.filter((x) => x === "approved").length}/6 gates · {d.pendingGate !== null ? `gate ${d.pendingGate} waits for you` : d.next} </Text>
        <Button key="show" label="show pane" onPress={() => show($)} />
      </Box>
    );
  });
};
