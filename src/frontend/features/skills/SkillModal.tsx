import { FileText, Terminal, Trash2, X } from "lucide-react";
import { Button, Markdown, Spinner } from "../../components/ui";
import { SkillItem } from "./lib";

export function SkillModal({ selectedSkill, detail, loadingDetail, onClose, onDelete }: { selectedSkill: SkillItem; detail: any; loadingDetail: boolean; onClose: () => void; onDelete?: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-[#0b1329]">
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-slate-100 p-5 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                {selectedSkill.name}
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                  v{selectedSkill.version || "1.4.0"}
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Bound Agents: {selectedSkill.agents.join(", ") || "All Agents"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div className="rounded-xl border border-slate-200 p-4 text-xs text-slate-600 dark:border-slate-800 dark:text-slate-300">
            <span className="font-bold">Security scan: not run.</span> This skill has not been scanned. NVIDIA SkillSpector scanning arrives with the
            rebuilt evaluator (plan P6); until then no security score is shown. SHA-256 <span className="mono">{selectedSkill.sha256}</span>
          </div>

          {/* Description & References */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Purpose & Description
            </h4>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              {selectedSkill.description}
            </p>
            {selectedSkill.references.length > 0 && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
                <FileText className="h-3.5 w-3.5" />
                <span>Included Standards & References:</span>
                <span className="font-mono text-indigo-600 dark:text-indigo-400">
                  {selectedSkill.references.join(", ")}
                </span>
              </div>
            )}
          </div>

          {/* Raw Skill Markdown Instruction Content */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Skill Instructions & Policy Definition
            </h4>
            {loadingDetail ? (
              <div className="py-8 text-center"><Spinner /></div>
            ) : detail?.body ? (
              <div className="max-h-96 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs dark:border-slate-800 dark:bg-slate-900 leading-relaxed text-slate-800 dark:text-slate-200">
                <Markdown>{detail.body}</Markdown>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No detailed instruction body available.</p>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-slate-100 p-4 dark:border-slate-800">
          <span className="text-xs text-slate-400">
            Loaded into multi-agent instruction pipeline
          </span>
          <div className="flex items-center gap-2">
            {onDelete && <Button 
              variant="danger" 
              onClick={() => onDelete()}
              className="flex items-center gap-1.5 text-rose-600 hover:text-white hover:bg-rose-600 border-rose-200 dark:border-rose-900"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Delete Skill</span>
            </Button>}
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button
              onClick={() => {
                window.location.href = `/harness?skill=${encodeURIComponent(selectedSkill.name)}`;
              }}
              className="flex items-center gap-1.5"
            >
              <Terminal className="h-3.5 w-3.5" />
              <span>Load into Harness</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
