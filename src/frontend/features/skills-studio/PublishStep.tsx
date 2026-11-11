import { useEffect, useState } from "react";
import { Button, Card, Empty } from "../../components/ui";
import { api, when } from "../../lib/api";
import { ChecksList } from "./ChecksList";
import { PlanRecord, Published } from "./types";
import { CallStatus, useCall } from "./useCall";

export type VersionRow = { name: string; version: number; sha256: string; author: string; created_at: string };

export function Versions({ name, reload }: { name: string; reload: number }) {
  const [rows, setRows] = useState<VersionRow[] | null>(null);
  useEffect(() => { api(`/skill-studio/skills/${name}/versions`).then((r) => setRows(r.versions)).catch(() => setRows([])); }, [name, reload]);
  if (rows && rows.length === 0) return <Empty title="No published versions yet." />;
  return (
    <ul className="space-y-1" data-testid="studio-versions">
      {rows?.map((v) => (
        <li key={v.version} className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-semibold">v{v.version}</span><span className="mono">{v.sha256.slice(0, 12)}</span><span className="text-slate-500">{v.author}, {when(v.created_at)}</span>
          <a className="text-indigo-600 underline" href={`/api/skill-studio/skills/${v.name}/versions/${v.version}/zip`} download>Download zip</a>
        </li>
      ))}
    </ul>
  );
}

export function PublishStep({ record }: { record: PlanRecord }) {
  const [done, setDone] = useState<Published | null>(null);
  const call = useCall();
  const publish = () => call.run("Publishing…", async () => setDone(await api(`/skill-studio/plans/${record.id}/publish`, { method: "POST" })));
  return (
    <Card title="8. Publish">
      <div className="space-y-3">
        <Button onClick={publish} disabled={!!call.busy} busy={!!call.busy} data-testid="studio-publish">Publish skill</Button>
        <CallStatus call={call} />
        {done && (
          <div className="space-y-2 text-sm">
            <p>Published <span className="font-semibold">{done.name}</span> version <span data-testid="studio-version">{done.version}</span>, SHA-256 <span className="mono text-xs">{done.sha256}</span></p>
            <ChecksList checks={done.checks} />
          </div>
        )}
        <Versions name={record.plan.name} reload={done?.version ?? 0} />
      </div>
    </Card>
  );
}
