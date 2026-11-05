"use client";

import { useRouter } from "next/navigation";
import { AppShell } from "../../components/AppShell";
import { HarnessView } from "../../components/HarnessView";

export default function GlobalHarnessPage() {
  const router = useRouter();

  return (
    <AppShell>
      <HarnessView
        onProjectChange={(newProjectId) => {
          if (newProjectId) {
            router.push(`/projects/${newProjectId}/harness`);
          }
        }}
      />
    </AppShell>
  );
}
