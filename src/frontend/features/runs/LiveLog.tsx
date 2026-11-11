"use client";

import { useEffect, useRef, useState } from "react";

export function LiveLog({ events, live }: { events: any[]; live: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);
  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [events, follow]);
  const color: Record<string, string> = { error: "text-rose-400", warning: "text-amber-400", review: "text-sky-300", test: "text-emerald-300", artifact: "text-emerald-300", agent: "text-indigo-300", agent_call: "text-indigo-300", skill: "text-fuchsia-300", tool: "text-slate-400" };
  return (
    <div data-testid="live-log">
      <div className="mb-1 flex items-center justify-between text-xs">
        <b className="flex items-center gap-1.5">{live && <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />}{live ? "Live log" : "Run log"} ({events.length})</b>
        <label className="flex items-center gap-1 text-slate-500"><input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} /> Follow</label>
      </div>
      <div ref={box} className="mono max-h-72 overflow-y-auto rounded-lg bg-[#070d1f] p-2 text-[11px] leading-relaxed text-slate-300">
        {events.map((e) => (
          <div key={e.seq} className="flex gap-2">
            <span className="shrink-0 text-slate-500">{new Date(e.ts).toLocaleTimeString()}</span>
            {e.stage && <span className="w-24 shrink-0 truncate text-slate-500">{e.stage}</span>}
            <span className={`min-w-0 break-words ${color[e.type] || ""}`}>{e.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
