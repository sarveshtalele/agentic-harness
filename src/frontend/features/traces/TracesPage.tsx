"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { RunsTable } from "./RunsTable";
import { RunView } from "./RunView";

/** /traces lists runs; /traces?trace=<id> opens one, so a run can be linked to from anywhere. */
export function TracesPage() {
  const router = useRouter();
  const traceId = useSearchParams().get("trace") || "";
  return traceId ? <RunView traceId={traceId} onBack={() => router.push("/traces")} /> : <RunsTable onOpen={(id) => router.push(`/traces?trace=${encodeURIComponent(id)}`)} />;
}
