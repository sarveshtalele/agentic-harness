"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useProject } from "../../components/ProjectShell";
import { useAuth } from "../../components/AuthGate";
import { ConfirmModal } from "../../components/ConfirmModal";
import { Badge, Card, ErrorNote, inputClass, Spinner } from "../../components/ui";
import { AgentBar, ReviewResult } from "./AgentBar";
import { DocumentEditor } from "./DocumentEditor";
import { DocumentHeader } from "./DocumentHeader";
import { DocumentTabs } from "./DocumentTabs";
import { GherkinVisualizer } from "./gherkin/GherkinVisualizer";
import { SaveBar } from "./SaveBar";
import { useDocument } from "./useDocument";
import { VersionHistory } from "./VersionHistory";

export function DocumentPage() {
  const { project } = useProject();
  const { docId } = useParams<{ docId: string }>();
  const { user } = useAuth();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const { doc, draft, setDraft, note, setNote, tab, setTab, versions, viewing, setViewing, diff, setDiff, error, setError, busy, working, reviewResult, refineText, setRefineText, dirty, save, approve, restore, remove, review, refine } = useDocument(docId, project.id);

  if (!doc) return error ? <ErrorNote message={error} /> : <Spinner />;
  const isGherkin = doc.kind === "gherkin";
  const hasGherkin = isGherkin || /^(Feature:|Scenario:)/m.test(draft);
  const formats = isGherkin ? ["feature", "md", "docx"] : doc.kind === "patch" ? ["patch"] : doc.kind === "test_cases" ? ["md", "docx", "csv", "jira"] : ["md", "docx"];
  const agentEditable = ["brd", "prd", "stories", "gherkin"].includes(doc.kind);
  return (
    <>
      <DocumentHeader doc={doc} project={project} docId={docId} formats={formats} isGherkin={isGherkin} onApprove={approve} onDelete={() => setShowDeleteModal(true)} />
      {isGherkin && doc.gherkin && <p className="mb-2 text-xs" data-testid="gherkin-status">{doc.gherkin.valid ? <Badge tone="emerald">{`Valid Gherkin: ${doc.gherkin.scenarios} scenarios, ${doc.gherkin.steps} steps`}</Badge> : <Badge tone="rose">Invalid Gherkin</Badge>}</p>}
      <DocumentTabs tab={tab} setTab={setTab} hasGherkin={hasGherkin} versionCount={versions.length} />
      <ErrorNote message={error} />
      {agentEditable && <AgentBar working={working} refineText={refineText} setRefineText={setRefineText} dirty={!!dirty} onReview={review} onRefine={refine} />}
      {reviewResult && <ReviewResult reviewResult={reviewResult} />}
      {tab === "document" && (
        <Card>
          {doc.kind === "patch"
            ? <pre className="mono overflow-auto text-xs">{draft}</pre>
            : <DocumentEditor documentId={docId} value={draft} gherkin={isGherkin} onChange={setDraft} onError={setError} />}
        </Card>
      )}
      {tab === "scenarios" && (
        <div className="space-y-4">
          <GherkinVisualizer content={draft} />
        </div>
      )}
      {tab === "source" && (
        <div className="grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
          <textarea aria-label="Document content" name="doc-content" spellCheck={false} className={`${inputClass} mono min-h-[65vh] text-[13px] leading-relaxed`} value={draft} onChange={(e) => setDraft(e.target.value)} />
          <div className="max-h-[75vh] overflow-auto" data-testid="source-preview"><Card>{doc.kind === "patch" ? <pre className="mono overflow-auto text-xs">{draft}</pre> : <DocumentEditor documentId={docId} value={draft} gherkin={isGherkin} readOnly />}</Card></div>
        </div>
      )}
      {tab !== "history" && <SaveBar doc={doc} user={user} note={note} setNote={setNote} busy={busy} dirty={!!dirty} onSave={save} onDiscard={() => setDraft(doc.content)} />}
      {tab === "history" && <VersionHistory versions={versions} viewing={viewing} diff={diff} docId={docId} setViewing={setViewing} setDiff={setDiff} restore={restore} />}

      {/* Confirmation Modal for Document Deletion */}
      <ConfirmModal
        isOpen={showDeleteModal}
        title="Delete Specification Document"
        description={`Are you sure you want to permanently delete "${doc.title}" and all ${doc.current_version ?? 1} versions? This deletion will be recorded in the audit ledger.`}
        tone="danger"
        confirmText="Delete Document"
        onConfirm={remove}
        onClose={() => setShowDeleteModal(false)}
      />
    </>
  );
}
