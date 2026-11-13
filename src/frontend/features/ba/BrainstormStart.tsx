"use client";

import { Lightbulb } from "lucide-react";
import { useState } from "react";
import { Button, Card, inputClass } from "../../components/ui";

/** Step 1 of brainstorming (plan 12.4): what is needed, in a sentence or two, with the sources ticked on the right. The
 * agent reads the sources first, then asks one question at a time below. */
export function BrainstormStart({ busy, sources, onStart }: { busy: boolean; sources: number; onStart: (need: string) => void }) {
  const [need, setNeed] = useState("");
  return (
    <Card title={<span className="flex items-center gap-1.5"><Lightbulb className="h-4 w-4" /> Brainstorm a BRD</span>}>
      <p className="mb-2 text-xs text-slate-500">
        Describe what you need. The analyst agent reads the {sources ? `${sources} selected source${sources > 1 ? "s" : ""}` : "sources you select"} first,
        then asks one question at a time, offers approaches for you to pick, and writes the BRD for you to review and sign.
      </p>
      <textarea aria-label="What you need" className={`${inputClass} min-h-[4.5rem]`} placeholder="Customers can refund part of an order within 30 days"
        value={need} onChange={(e) => setNeed(e.target.value)} />
      <div className="mt-2 flex justify-end">
        <Button busy={busy} disabled={!need.trim()} onClick={() => onStart(need)}>Start brainstorming</Button>
      </div>
    </Card>
  );
}
