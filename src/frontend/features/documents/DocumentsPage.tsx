"use client";

import { Empty, PageTitle, Spinner } from "../../components/ui";
import { ConfirmModal } from "../../components/ConfirmModal";
import { useProject } from "../../components/ProjectShell";
import { DocumentFilters } from "./DocumentFilters";
import { DocumentsTable } from "./DocumentsTable";
import { downloadDoc } from "./lib";
import { NewDocumentCard } from "./NewDocumentCard";
import { useDocuments } from "./useDocuments";

export function DocumentsPage() {
  const { project } = useProject();
  const { docs, kind, setKind, query, setQuery, title, setTitle, template, setTemplate, safeTemplates, error, docToDelete, setDocToDelete, executeDeleteDoc, create } = useDocuments(project);

  if (!docs) return <Spinner />;
  const safeDocs = Array.isArray(docs) ? docs : [];
  const kinds = [...new Set(safeDocs.map((d) => d?.kind).filter(Boolean))];
  const shown = safeDocs.filter(
    (d) => d && (!kind || d.kind === kind) && (d.title || "").toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageTitle
        title="Governed Project Documents"
        subtitle="Versioned requirements, test plans, and release evidence isolated to this project with unique governance IDs."
      />

      <NewDocumentCard title={title} setTitle={setTitle} template={template} setTemplate={setTemplate} templates={safeTemplates} onCreate={create} error={error} />

      {safeDocs.length > 0 && (
        <DocumentFilters query={query} setQuery={setQuery} kind={kind} setKind={setKind} kinds={kinds} shownCount={shown.length} total={safeDocs.length} />
      )}

      {shown.length ? (
        <DocumentsTable shown={shown} project={project} onDownload={downloadDoc} onDelete={setDocToDelete} />
      ) : (
        <Empty title="No documents found">
          Generate one in BA Studio or start from a template above.
        </Empty>
      )}

      {/* Confirmation Modal for Document Deletion */}
      <ConfirmModal
        isOpen={!!docToDelete}
        title="Delete Specification Document"
        description={`Are you sure you want to permanently delete "${docToDelete?.title}"? All versions will be removed from this project.`}
        tone="danger"
        confirmText="Delete Document"
        onConfirm={executeDeleteDoc}
        onClose={() => setDocToDelete(null)}
      />
    </div>
  );
}
