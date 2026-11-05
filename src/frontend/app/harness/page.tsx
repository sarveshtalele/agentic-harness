"use client";

import { Suspense } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "../../components/AppShell";
import { HarnessView } from "../../components/HarnessView";

function HarnessContent() {
  const router = useRouter();

  return (
    <HarnessView
      onProjectChange={(newProjectId) => {
        if (newProjectId) {
          router.replace(`/harness?project=${newProjectId}`);
        }
      }}
    />
  );
}

export default function GlobalHarnessPage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="p-8 text-center text-sm text-slate-400">Loading QE Harness...</div>}>
        <HarnessContent />
      </Suspense>
    </AppShell>
  );
}
