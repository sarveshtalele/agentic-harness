"use client";

import { useState } from "react";
import { Badge, Button, ErrorNote, inputClass } from "../../components/ui";
import { api } from "../../lib/api";

const area = `${inputClass} min-h-[4.5rem]`;

/** A brainstorm step in BA Studio (plan 12.4): a question with its reason and source and an editable play-back; the
 * approaches to pick from; or the builder check's questions. Each answer is a recorded decision by the signed-in person. */
export function BrainstormStep({ approval, onDecided }: { approval: any; onDecided: () => void }) {
  const p = approval.payload || {};
  const [question, setQuestion] = useState(p.question || "");
  const [understood, setUnderstood] = useState(p.understood || "");
  const [answer, setAnswer] = useState("");
  const [answers, setAnswers] = useState<string[]>((p.questions || []).map(() => ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const send = async (body: Record<string, unknown>, approved = true) => {
    setBusy(true);
    setError("");
    try {
      await api(`/approvals/${approval.id}/decide`, { json: { approved, ...body } });
      onDecided();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const stop = <Button variant="secondary" busy={busy} onClick={() => send({ feedback: "Stopped by the analyst" }, false)}>Stop</Button>;

  return (
    <article className="space-y-3 rounded-xl border border-indigo-500/50 bg-indigo-500/5 p-4" data-testid="brainstorm-step">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="indigo">Brainstorm</Badge>
        <h3 className="text-sm font-bold">{approval.title}</h3>
      </div>
      {p.kind === "brainstorm_question" && (
        <>
          <label className="block text-xs font-semibold">What I understood so far
            <textarea aria-label="What I understood so far" className={area} value={understood} onChange={(e) => setUnderstood(e.target.value)} />
          </label>
          <label className="block text-xs font-semibold">Question
            <textarea aria-label="Question" className={area} value={question} onChange={(e) => setQuestion(e.target.value)} />
          </label>
          <p className="text-xs text-slate-500">Why I ask: {p.why || "—"} · From: {p.source || "—"}</p>
          <label className="block text-xs font-semibold">Your answer
            <textarea aria-label="Your answer" className={area} value={answer} onChange={(e) => setAnswer(e.target.value)} />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button busy={busy} disabled={!answer.trim()} onClick={() => send({ action: "answer", answer, question, understood })}>Answer</Button>
            <Button variant="secondary" busy={busy} onClick={() => send({ action: "skip", question, understood })}>Skip</Button>
            <Button variant="secondary" busy={busy} onClick={() => send({ action: "propose", question, understood })}>I don&apos;t know, propose something</Button>
            {stop}
          </div>
          {(p.history || []).length > 0 && (
            <details className="text-xs"><summary>Earlier questions ({p.history.length})</summary>
              <ol className="list-decimal space-y-1 pl-5">{p.history.map((h: any, i: number) => <li key={i}><b>{h.question}</b> {h.answer}</li>)}</ol>
            </details>
          )}
        </>
      )}
      {p.kind === "brainstorm_approaches" && (
        <div className="space-y-2">
          {(p.approaches || []).map((a: any, i: number) => (
            <div key={a.name} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
              <div className="flex flex-wrap items-center gap-2 font-semibold">{a.name}{i === p.recommended && <Badge tone="emerald">recommended</Badge>}</div>
              <p className="text-slate-600 dark:text-slate-300">{a.summary}</p>
              <p className="text-xs text-slate-500">Trade-offs: {a.tradeoffs}</p>
              <Button className="mt-2" busy={busy} onClick={() => send({ choice: i })}>Choose this</Button>
            </div>
          ))}
          {stop}
        </div>
      )}
      {p.kind === "builder_check" && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">The builder check found questions only you can answer. The draft is revised once with your answers.</p>
          {(p.questions || []).map((q: string, i: number) => (
            <label key={q} className="block text-xs font-semibold">{q}
              <textarea aria-label={q} className={area} value={answers[i] || ""} onChange={(e) => setAnswers((all) => all.map((x, j) => (j === i ? e.target.value : x)))} />
            </label>
          ))}
          <div className="flex gap-2"><Button busy={busy} onClick={() => send({ answers })}>Send answers</Button>{stop}</div>
        </div>
      )}
      <ErrorNote message={error} />
    </article>
  );
}
