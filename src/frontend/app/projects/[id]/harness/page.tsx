"use client";

import { useParams, useRouter } from "next/navigation";
import { ProjectShell } from "../../../../components/ProjectShell";
import { HarnessView } from "../../../../components/HarnessView";

export default function ProjectHarnessPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  return (
    <ProjectShell>
      <HarnessView
        initialProjectId={id}
        onProjectChange={(newProjectId: string) => {
          if (newProjectId && newProjectId !== id) {
            router.push(`/projects/${newProjectId}/harness`);
          }
        }}
      />
    </ProjectShell>
  );
}
