import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge, Card, ErrorNote, Spinner } from "../../components/ui";
import { useAuth } from "../../components/AuthGate";
import { api } from "../../lib/api";
import { EvaluateStep } from "./EvaluateStep";
import { GenerateStep } from "./GenerateStep";
import { KindStep } from "./KindStep";
import { PlanEditor } from "./PlanEditor";
import { PublishStep } from "./PublishStep";
import { RequestStep } from "./RequestStep";
import { SourceStep } from "./SourceStep";
import { TestStep } from "./TestStep";
import { UploadCard } from "./UploadCard";
import { Kind, PlanRecord, Project, Source } from "./types";
import { useCall } from "./useCall";

export function Studio({ planId }: { planId: string }) {
  const router = useRouter();
  const viewer = useAuth().user?.role === "viewer";
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [source, setSource] = useState<Source | null>(null);
  const [kind, setKind] = useState<Kind | "">("");
  const [request, setRequest] = useState("");
  const [record, setRecord] = useState<PlanRecord | null>(null);
  const [loadError, setLoadError] = useState("");
  const draftCall = useCall();
  useEffect(() => {
    api("/projects").then((r) => setProjects(Array.isArray(r) ? r : r.projects)).catch((e) => setLoadError(e.message));
  }, []);
  useEffect(() => {
    if (!planId) { setRecord(null); return; }
    api(`/skill-studio/plans/${planId}`).then(setRecord).catch((e) => setLoadError(e.message));
  }, [planId]);
  const draft = () => draftCall.run("Drafting the plan with the model…", async () => {
    const made: PlanRecord = await api("/skill-studio/plans", { json: { project_id: projectId, kind, source, request } });
    setRecord(made);
    router.replace(`/skills/studio?plan=${made.id}`);
  });
  const ready = !!projectId && !!source && !!kind;
  const status = record?.status;
  if (planId && !record && !loadError) return <Spinner label="Loading the plan…" />;
  return (
    <fieldset disabled={viewer} className="min-w-0 space-y-4 border-0 p-0">
      {viewer && <p role="status" className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">You have the viewer role, so this page is read-only. Ask an administrator for a BA, developer or QE lead role to create skills.</p>}
      <ErrorNote message={loadError} />
      {record ? (
        <>
          <div data-testid="studio-step-3"><Card title="Steps 1 to 3: source, kind and request" actions={<button type="button" className="text-xs text-indigo-600 underline" onClick={() => { setRecord(null); router.replace("/skills/studio"); }}>Start a new plan</button>}>
            <p className="text-xs text-slate-500">Kind <Badge tone="indigo">{record.kind}</Badge> · source SHA-256 <span className="mono">{record.source_sha256.slice(0, 12)}</span> · prompt <span className="mono">{record.prompt_ref}</span></p>
            {record.request && <p className="mt-2 text-sm">{record.request}</p>}
          </Card></div>
          <div data-testid="studio-step-4"><PlanEditor record={record} onRecord={setRecord} /></div>
          {status !== "draft" && <div data-testid="studio-step-5"><GenerateStep record={record} onRecord={setRecord} /></div>}
          {status === "generated" && (
            <>
              <div data-testid="studio-step-6"><TestStep record={record} /></div>
              <div data-testid="studio-step-7"><EvaluateStep record={record} /></div>
              <div data-testid="studio-step-8"><PublishStep record={record} /></div>
            </>
          )}
        </>
      ) : (
        <>
          <div data-testid="studio-step-1"><SourceStep projects={projects} projectId={projectId} onProject={setProjectId} onSource={setSource} /></div>
          <div data-testid="studio-step-2"><KindStep kind={kind} onKind={setKind} /></div>
          <div data-testid="studio-step-3"><RequestStep request={request} onRequest={setRequest} ready={ready} call={draftCall} onDraft={draft} /></div>
        </>
      )}
      <div data-testid="studio-step-9"><UploadCard projectId={record?.project_id ?? projectId} /></div>
    </fieldset>
  );
}
