"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "../../components/AppShell";
import { HarnessView } from "../../components/HarnessView";
import { MafHarness } from "../../components/MafHarness";

function HarnessContent() {
  const router = useRouter();
  const params = useSearchParams();
  const project = params.get("project") || "";
  const onProjectChange = (newProjectId: string) => {
    if (newProjectId) router.replace(`/harness?${params.get("engine") === "legacy" ? "engine=legacy&" : ""}project=${newProjectId}`);
  };

  // The MAF harness is the default; the earlier hand-written engine stays reachable until the owner retires it.
  if (params.get("engine") === "legacy") return <HarnessView onProjectChange={onProjectChange} />;
  return <MafHarness projectId={project} onProjectChange={onProjectChange} />;
}

export default function GlobalHarnessPage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="p-8 text-center text-sm text-slate-400">Loading harness...</div>}>
        <HarnessContent />
      </Suspense>
    </AppShell>
  );
}
