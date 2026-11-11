"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../../../components/AppShell";
import { PageTitle } from "../../../components/ui";
import { Studio } from "../../../features/skills-studio/Studio";

function StudioContent() {
  return <Studio planId={useSearchParams().get("plan") || ""} />;
}

export default function SkillStudioPage() {
  return (
    <AppShell>
      <PageTitle title="Skill Creator Studio" subtitle="AI Architect: draft a plan from your source, approve it, generate the skill, test it, evaluate it on the model (Benchmark Quality), and publish a version." />
      <Suspense fallback={<p className="p-8 text-center text-sm text-slate-400">Loading…</p>}>
        <StudioContent />
      </Suspense>
    </AppShell>
  );
}
