import { useState } from "react";
import { Card } from "../../components/ui";
import { upload } from "../../lib/api";
import { ChecksList } from "./ChecksList";
import { Published } from "./types";
import { CallStatus, useCall } from "./useCall";

export function UploadCard({ projectId }: { projectId: string }) {
  const [done, setDone] = useState<Published | null>(null);
  const call = useCall();
  const send = (file?: File) => {
    if (!file) return;
    const form = new FormData(); form.append("project_id", projectId); form.append("file", file);
    setDone(null);
    call.run("Uploading and checking…", async () => setDone(await upload("/skill-studio/upload", form)));
  };
  return (
    <Card title="9. Upload a skill zip">
      <div className="space-y-3">
        <p className="text-xs text-slate-500">A zip of one skill folder. It gets the same checks as a generated skill and becomes a new version.</p>
        {!projectId && <p className="text-xs text-slate-500">Choose a project in step 1 first.</p>}
        <input type="file" accept=".zip" aria-label="Skill zip" data-testid="studio-upload" disabled={!projectId || !!call.busy} onChange={(e) => { send(e.target.files?.[0]); e.target.value = ""; }} className="text-sm" />
        <CallStatus call={call} />
        {done && <div className="space-y-2 text-sm" data-testid="studio-upload-result"><p>Uploaded {done.name} as version {done.version}, SHA-256 <span className="mono text-xs">{done.sha256}</span></p><ChecksList checks={done.checks} /></div>}
      </div>
    </Card>
  );
}
