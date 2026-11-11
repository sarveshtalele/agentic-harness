import { Badge, Button, Card, inputClass } from "../../components/ui";

type Props = { working: string; refineText: string; setRefineText: (v: string) => void; dirty: boolean; onReview: () => void; onRefine: () => void };

export function AgentBar({ working, refineText, setRefineText, dirty, onReview, onRefine }: Props) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <Button variant="secondary" busy={working === "review"} onClick={onReview}>Ask reviewer</Button>
      <input aria-label="Refine instructions" className={`${inputClass} max-w-md`} placeholder="Tell the agent what to change" value={refineText} onChange={(e) => setRefineText(e.target.value)} />
      <Button variant="secondary" busy={working === "refine"} disabled={!refineText.trim() || dirty} title={dirty ? "Save your edits first" : undefined} onClick={onRefine}>Refine with agent</Button>
    </div>
  );
}

export function ReviewResult({ reviewResult }: { reviewResult: any }) {
  return (
    <div className="mb-3"><Card title={<span>Review of v{reviewResult.version}: score {reviewResult.score} <Badge>{reviewResult.verdict}</Badge></span>}><ul className="list-disc space-y-0.5 pl-5 text-sm">{Array.isArray(reviewResult.issues) && reviewResult.issues.map((i: string, n: number) => <li key={n}>{i}</li>)}</ul></Card></div>
  );
}
