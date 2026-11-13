import { Download, FolderArchive } from "lucide-react";

export function SetupPackageCard({ project }: { project: any }) {
  return (
    <div className="rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50/50 via-slate-50/30 to-white p-4 shadow-sm dark:border-indigo-950/60 dark:from-indigo-950/20 dark:to-[#0b1329]">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-md">
            <FolderArchive className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Download a runnable copy
            </h3>
            <p className="text-xs text-slate-500">
              One ZIP with the project&apos;s source, its generated tests, and setup scripts for macOS and Linux (<code>setup_mac_linux.sh</code>) and Windows (<code>setup_windows.bat</code>).
            </p>
          </div>
        </div>

        <a
          href={`/api/projects/${project.id}/export-zip`}
          download={`${project.id}_sdlc_export.zip`}
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-indigo-700 transition-colors"
        >
          <Download className="h-4 w-4" /> Download (.zip)
        </a>
      </div>
    </div>
  );
}
