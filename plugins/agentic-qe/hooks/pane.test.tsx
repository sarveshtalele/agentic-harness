// Run with: npm run test:pane (claude plugin test on a copy that holds only the mod)
import { expect, test } from "claude-code/testing";

const PANE = { plugin: "agentic-qe", component: "Pane", requestId: "agentic-qe", props: { title: "Agentic QE", isFocused: false, bodyColumns: 44, placement: "dock", scroll: { offset: 0, bodyRows: 40 }, view: {} } } as const;
const BAR = { plugin: "agentic-qe", component: "AbovePrompt", props: { hasSurvey: false, isWorking: false, maxRows: 3, bodyColumns: 80, scroll: { offset: 0, bodyRows: 3 }, view: {} } } as const;
const GATES_DONE = ["approved", "pending", "pending", "pending", "pending", "pending"];
const STATE = {
  app: "shop", mode: "brownfield", hasRun: true, phases: [{ id: "start", label: "Start", done: true, active: false, outOfOrder: false }],
  apps: ["shop"], gates: GATES_DONE, levels: {}, blockers: ["2 cases have no review"], ledger: { ok: true }, next: "/agentic-qe:qe-discover shop",
  approval: null as string | null, reject: null as string | null, pendingGate: null as number | null, gateReport: null as string | null, dashboard: null,
  cases: [{ id: "TC-SHOP-001", level: "Unit", status: "PASS", low: true }], low: 1, confidence: 82,
};

const WAITING = { ...STATE, approval: "approve gate 1", reject: "reject gate 1", pendingGate: 1, gateReport: "docs/qe/shop/01-requirements/gate-1-report.md" };

function engine(on: any, state: unknown, seen: string[] = [], registered: unknown[] = [], filled: string[] = [], opt: { placed?: boolean; submits?: { n: number }; afters?: { n: number } } = {}) {
  on("prompt.fill", (_: unknown, e: { text: string }) => { filled.push(e.text); return { isFilled: true }; });
  on("command.register", (_: unknown, e: unknown) => { registered.push(e); return { value: { command: "qe-pane" } }; });
  on("clock.every", () => ({ value: undefined }));
  on("clock.after", () => { if (opt.afters) opt.afters.n++; return { value: undefined }; });
  on("ui.open", () => ({ value: opt.placed === false ? { isPlaced: false, reason: "narrow" } : { isPlaced: true } }));
  on("ui.close", () => ({ value: undefined }));
  on("session.cwd", () => ({ value: "/project" }));
  on("process.run", (_: unknown, e: { argv: string[] }) => { seen.push(e.argv.join(" ")); return { value: { exitCode: 0, stdout: JSON.stringify(state), stderr: "" } }; });
  on("session.start", (_: unknown, e: { cwd: string }) => ({ cwd: e.cwd }));
  on("prompt.submit", (_: unknown, e: unknown) => { if (opt.submits) opt.submits.n++; return e; });
  return seen;
}

test("the pane draws the run on every surface and offers the next command", async ($, on) => {
  const seen = engine(on, STATE);
  await $.session.start({ cwd: "/project", surface: "desktop", isInteractive: true });
  expect(seen.some((c) => c.includes("panel.ts --json --root /project"))).toBe(true);
  for (const surface of ["terminal", "desktop", "vscode", "mobile"] as const) {
    const ui = await $.ui.mount({ ...PANE, surface });
    expect(await ui.find({ type: "Text", text: /Test cases 1 · confidence 82 · 1 low/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /2 cases have no review/ })).toBeDefined();
    expect(await ui.find({ key: "fill" })).toBeDefined();
    await ui.unmount();
  }
});

test("a waiting gate opens a review dialog; its buttons put the phrase in the prompt and never submit it", async ($, on) => {
  const filled: string[] = [];
  const submits = { n: 0 };
  engine(on, WAITING, [], [], filled, { submits });
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  const ui = await $.ui.mount({ ...PANE, surface: "terminal" });
  expect(await ui.find({ type: "Text", text: /Waiting for you: Gate 1 Requirements/ })).toBeDefined();
  expect(await ui.find({ key: "fill" })).toBeUndefined();
  await ui.press({ key: "review" });
  expect(await ui.find({ type: "Text", text: /gate-1-report\.md/ })).toBeDefined();
  await ui.press({ key: "approve" });
  expect(filled).toEqual(["approve gate 1"]);
  expect(submits.n).toBe(0);
  await ui.press({ key: "review" });
  await ui.press({ key: "reject" });
  expect(filled[1]).toBe("reject gate 1 ");
  await ui.unmount();
});

test("stop the run shows while a turn runs and aborts that turn", async ($, on) => {
  const aborted: string[] = [];
  engine(on, STATE);
  on("turn.abort", (_: unknown, e: { turnId: string }) => { aborted.push(e.turnId); return { value: undefined }; });
  on("turn.start", (_: unknown, e: unknown) => e as never);
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  await $.turn.start({ turnId: "t-42" } as never);
  const ui = await $.ui.mount({ ...PANE, surface: "terminal" });
  await ui.press({ key: "stop" });
  expect(aborted).toEqual(["t-42"]);
  await ui.unmount();
});

test("/qe-pane json prints the reading; close and open switch the pane", async ($, on) => {
  engine(on, STATE);
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  expect((await $.command.run({ command: "qe-pane", args: "json" } as never)).text).toContain('"app": "shop"');
  expect((await $.command.run({ command: "qe-pane", args: "close" } as never)).text).toContain("hidden");
  expect((await $.command.run({ command: "qe-pane", args: "open" } as never)).text).toContain("shown");
});

test("panel off: --watch does not open the pane and no bar is drawn", { options: { panel: "off" } }, async ($, on) => {
  const seen = engine(on, STATE);
  const before = seen.length;
  await $.prompt.submit({ text: "/agentic-qe:qe-panel shop --watch", wait: false, origin: "user" } as never);
  expect(seen.length).toBe(before);
});

test("a pane held back by a narrow terminal keeps the show bar", async ($, on) => {
  engine(on, STATE, [], [], [], { placed: false });
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  await $.command.run({ command: "qe-pane", args: "open" } as never);
  const bar = await $.ui.mount({ ...BAR, surface: "terminal" });
  expect(await bar.find({ key: "show" })).toBeDefined();
  await bar.unmount();
});

test("a ledger that is not trusted is named", async ($, on) => {
  engine(on, { ...STATE, ledger: { ok: false, reason: "no local anchor" } });
  await $.session.start({ cwd: "/project", surface: "desktop", isInteractive: true });
  const ui = await $.ui.mount({ ...PANE, surface: "desktop" });
  expect(await ui.find({ type: "Text", text: /no local anchor/ })).toBeDefined();
  await ui.unmount();
});

test("hide leaves one row above the prompt, and show pane brings the pane back", async ($, on) => {
  engine(on, STATE);
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  const pane = await $.ui.mount({ ...PANE, surface: "terminal" });
  await pane.press({ key: "hide" });
  await pane.unmount();
  const bar = await $.ui.mount({ ...BAR, surface: "terminal" });
  expect(await bar.find({ type: "Text", text: /QE shop: 1\/6 gates/ })).toBeDefined();
  await bar.press({ key: "show" });
  await bar.unmount();
});

test("--watch opens the pane instead of a second terminal; other prompts do not", async ($, on) => {
  const seen = engine(on, STATE);
  const before = seen.length;
  await $.prompt.submit({ text: "fix the login test", wait: false, origin: "user" } as never);
  expect(seen.length).toBe(before);
  await $.prompt.submit({ text: "/agentic-qe:qe-panel shop --watch", wait: false, origin: "user" } as never);
  expect(seen.length).toBe(before + 1);
});

test("/clear resets $.state; the pane reads the files again", async ($, on) => {
  const seen = engine(on, { ...STATE, hasRun: false });
  on("classic.SessionStart", () => ({}));
  await $.session.start({ cwd: "/project", surface: "desktop", isInteractive: true });
  const before = seen.length;
  await $.classic.SessionStart({ source: "clear" } as never);
  expect(seen.length).toBeGreaterThan(before);
});

test("/qe-pane runs at once, even while Claude is working", async ($, on) => {
  const registered: unknown[] = [];
  engine(on, STATE, [], registered);
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  expect(JSON.stringify(registered)).toContain('"immediate":true');
});

test("the pane shows coverage tiles, tests in the repo and the validator verdict, like the dashboard", async ($, on) => {
  engine(on, { ...STATE, coverage: { gate: 1, ok: true, gaps: [], more: 0, counts: { requirements: 7, scenarios: 109, cases: 26, tests: 8, results: 0 } }, inventory: { files: 19, tests: 61, existing: 11, generated: 50, manual: 0, byLevel: {} }, toGenerate: 83, validation: { gate: 3, ok: false, errors: 6, warnings: 3, first: "plan scenarios with no designed case" }, version: "1.6.0" });
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  const ui = await $.ui.mount({ ...PANE, surface: "terminal" });
  expect(await ui.find({ type: "Text", text: /^109$/ })).toBeDefined();
  expect(await ui.find({ type: "Text", text: /to generate/ })).toBeDefined();
  expect(await ui.find({ type: "Text", text: /existing 11 · generated 50 · added by hand 0/ })).toBeDefined();
  expect(await ui.find({ type: "Text", text: /pandas\/numpy validator, gate 3: FAIL · 6 errors/ })).toBeDefined();
  expect(await ui.find({ type: "Text", text: /v1\.6\.0/ })).toBeDefined();
  await ui.unmount();
});

test("export session runs the plugin's export script and says where the record is", async ($, on) => {
  const seen = engine(on, STATE);
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  const ui = await $.ui.mount({ ...PANE, surface: "terminal" });
  await ui.press({ key: "session" });
  expect(seen.some((c) => c.includes("export-session.ts --root /project --app shop"))).toBe(true);
  await ui.unmount();
});

test("a watched file changing outside Claude schedules a fresh reading", async ($, on) => {
  const afters = { n: 0 };
  engine(on, STATE, [], [], [], { afters });
  on("classic.FileChanged", () => ({}));
  await $.session.start({ cwd: "/project", surface: "terminal", isInteractive: true });
  const before = afters.n;
  await $.classic.FileChanged({ file_path: "/project/tests/a.test.ts", event: "change" } as never);
  expect(afters.n).toBe(before + 1);
});
