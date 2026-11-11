"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "../../components/AppShell";
import { MafHarness } from "../../components/MafHarness";

function HarnessContent() {
  const router = useRouter();
  const params = useSearchParams();
  const project = params.get("project") || "";
  const onProjectChange = (newProjectId: string) => {
    if (newProjectId) router.replace(`/harness?project=${newProjectId}`);
  };

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
