"use client";

import { Suspense } from "react";
import { AppShell } from "../../components/AppShell";
import { PageTitle, Spinner } from "../../components/ui";
import { TracesPage } from "../../features/traces/TracesPage";

export default function Traces() {
  return (
    <AppShell>
      <PageTitle title="Trace explorer" subtitle="Every chat turn, workflow run, and Skill Studio step as an OpenTelemetry trace: agents, model calls, tool calls, and stages, from the local span store." />
      <Suspense fallback={<Spinner />}>
        <TracesPage />
      </Suspense>
    </AppShell>
  );
}
