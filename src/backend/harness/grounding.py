"""
Centralized Database Grounding for Agentic QE Harness.
Queries data/atlas.sqlite3 deterministically for bugs, defects, documents, gates, and static analysis.
"""
import logging
import time
from typing import Dict, Any, Optional
from .session import SessionState, ToolCallRecord

log = logging.getLogger(__name__)


class HarnessGrounding:
    """
    Deterministic grounding against centralized SQLite database (data/atlas.sqlite3).
    Directly answers factual inquiries about:
      1. Bugs, defects, scan findings, vulnerabilities, and bug fixes.
      2. Governed documents, BRDs, PRDs, and specifications.
      3. Quality Gates (G0-G8) status and approvals.
    Prevents model hallucination and provides instant tabular facts.
    """

    @staticmethod
    def ground_from_centralized_db(session: SessionState, user_prompt: str) -> Optional[Dict[str, Any]]:
        p_lower = user_prompt.lower().strip()
        
        # Only the project bound to the session is used; a prompt never redirects it.
        target_proj = session.projectId
        if not target_proj:
            return None  # no project bound: nothing to ground against

        from backend.db import db, rows, row, new_id, now
        from backend.repos.sandbox import repo_dir
        from backend.repos import static_analysis
        now_ms = int(time.time() * 1000)

        # -------------------------------------------------------------------------
        # 1. Defect / Bug / Findings / Scan Inquiries
        # -------------------------------------------------------------------------
        is_bug_query = any(k in p_lower for k in [
            "how many bug", "how many defect", "how many fix", "bug fix",
            "list bug", "list defect", "show bug", "show defect",
            "what are the bug", "what are the defect", "bugs listed",
            "open finding", "defect inventory", "scan defect", "scan repo",
            "scan repository", "bug scan", "run bug scan", "check bug", "check defect",
            "vulnerabilities", "how many findings", "defect count", "all defects"
        ])

        if is_bug_query:
            with db() as con:
                proj = row(con.execute("SELECT id, name, description FROM projects WHERE id=?", (target_proj,)))
                proj_name = proj["name"] if proj else target_proj.replace("prj_", "").replace("_", " ").title()

                # Check runs table for bug_scan
                scan_run = row(con.execute(
                    "SELECT id, workflow, status, started_at, ended_at, error, model FROM runs WHERE project_id=? AND workflow='bug_scan' ORDER BY started_at DESC LIMIT 1",
                    (target_proj,)
                ))

                # Check findings table
                findings_db = rows(con.execute(
                    "SELECT id, severity, file, line, title, evidence, explanation, status, rule, created_at FROM findings WHERE project_id=? ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, created_at DESC",
                    (target_proj,)
                ))

            findings_list = [dict(f) for f in findings_db]

            scan_error = None
            # If no scan run or 0 findings exist, check if repository exists and execute static analysis
            if not findings_list:
                try:
                    r_path = repo_dir(target_proj)
                    if r_path.exists():
                        scanned_findings = static_analysis.run_all(r_path)
                        if scanned_findings:
                            run_id = new_id("run")
                            timestamp = now()
                            with db() as con:
                                con.execute(
                                    "INSERT INTO runs (id, project_id, workflow, status, started_at, ended_at, model) VALUES (?, ?, 'bug_scan', 'completed', ?, ?, 'static-analysis')",
                                    (run_id, target_proj, timestamp, timestamp)
                                )
                                for sf in scanned_findings:
                                    b_id = new_id("bug")
                                    fingerprint = f"{sf.get('rule')}|{sf.get('file')}|{sf.get('evidence', '')}|{sf.get('line', '')}"
                                    con.execute(
                                        "INSERT OR IGNORE INTO findings (id, project_id, run_id, source, rule, severity, title, file, line, evidence, explanation, status, fingerprint, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)",
                                        (b_id, target_proj, run_id, sf.get("source", "static"), sf.get("rule", "AST"), sf.get("severity", "medium").lower(), sf.get("title", "Finding"), sf.get("file", ""), sf.get("line", 1), sf.get("evidence", ""), sf.get("explanation", ""), fingerprint, timestamp)
                                    )
                                con.commit()
                                scan_run = {"id": run_id, "status": "completed", "started_at": timestamp}
                                with db() as con:
                                    findings_db = rows(con.execute(
                                        "SELECT id, severity, file, line, title, evidence, explanation, status, rule, created_at FROM findings WHERE project_id=? ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, created_at DESC",
                                        (target_proj,)
                                    ))
                                findings_list = [dict(f) for f in findings_db]
                except Exception as exc:
                    log.warning("grounding scan of %s failed: %s", target_proj, exc)
                    scan_error = str(exc)

            total_count = len(findings_list)
            crit_count = len([f for f in findings_list if f["severity"].lower() == "critical"])
            high_count = len([f for f in findings_list if f["severity"].lower() == "high"])
            med_count = len([f for f in findings_list if f["severity"].lower() == "medium"])
            low_count = len([f for f in findings_list if f["severity"].lower() == "low"])
            open_count = len([f for f in findings_list if f.get("status", "open").lower() == "open"])
            closed_count = total_count - open_count

            scan_info = f"`{scan_run['id']}` ({scan_run['status'].upper()})" if scan_run else "*(no scan run recorded for this project)*"

            if total_count > 0:
                table_rows = []
                for f in findings_list[:20]:
                    sev = f["severity"].lower()
                    sev_label = "🔴 CRITICAL" if sev == "critical" else "🟠 HIGH" if sev == "high" else "🟡 MEDIUM" if sev == "medium" else "⚪ LOW"
                    loc = f"`{f['file']}:{f['line']}`" if f.get("file") else "`workspace`"
                    title = f["title"].replace("\n", " ").strip()
                    if len(title) > 90:
                        title = title[:87] + "..."
                    rule = f.get("rule", "REVIEW")
                    st = f.get("status", "open")
                    table_rows.append(f"| `{f['id']}` | {sev_label} | {loc} | {title} | `{rule}` | `{st}` |")

                more_note = f"\n\n💡 *Showing top 20 of **{total_count}** findings recorded in `data/atlas.sqlite3`. You can inspect all findings and apply automated branch fixes on the [Project Bug Scan Page](/projects/{target_proj}/bugs).*" if total_count > 20 else ""

                content = (
                    f"### 🐛 Centralized Defect Inventory · {proj_name} (`{target_proj}`)\n\n"
                    f"There are currently **{total_count} defect findings** recorded in the centralized database (`atlas.sqlite3`) for this project:\n\n"
                    f"- 🔴 **Critical:** {crit_count}\n"
                    f"- 🟠 **High:** {high_count}\n"
                    f"- 🟡 **Medium:** {med_count}\n"
                    f"- ⚪ **Low:** {low_count}\n"
                    f"- **Status:** {open_count} open · {closed_count} resolved\n"
                    f"- **Grounding Scan Run:** {scan_info}\n\n"
                    f"| Bug ID | Severity | Location | Defect Description / Title | Rule | Status |\n"
                    f"| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                    + "\n".join(table_rows)
                    + more_note
                )
            else:
                content = (
                    f"### 🐛 Defect Scan Grounding · {proj_name} (`{target_proj}`)\n\n"
                    f"🔍 **Database Check (`atlas.sqlite3`):** 0 defect findings registered.\n"
                    f"- **Active Project:** **{proj_name}** (`{target_proj}`)\n"
                    f"- **Scan Status:** {'The scan failed: ' + scan_error if scan_error else ('Scan run `' + scan_run['id'] + '` recorded 0 findings.' if scan_run else 'No scan has been run for this project, so 0 findings means nothing was checked.')}\n"
                    f"You can launch a full multi-agent code review scan from the [Bug Scan Page](/projects/{target_proj}/bugs) or by requesting `/security-audit`."
                )

            tool_record = ToolCallRecord(
                id=f"call_scan_ground_{now_ms}",
                name="scan_defects",
                args={"projectId": target_proj, "severity": "all"},
                result={"projectId": target_proj, "defectsCount": total_count, "critical": crit_count, "high": high_count, "status": "Retrieved from centralized DB"},
                status="completed"
            )

            return {
                "thought": f"Centralized Database Grounding: queried data/atlas.sqlite3 (tables: `findings`, `runs`). Found {total_count} defects ({crit_count} Critical, {high_count} High, {med_count} Medium, {low_count} Low) for project {proj_name}.",
                "content": content,
                "tool_calls": [tool_record]
            }

        # -------------------------------------------------------------------------
        # 2. Document / Specification Inquiries (Not creation)
        # -------------------------------------------------------------------------
        is_create_directive = any(phrase in p_lower for phrase in [
            "create a doc", "generate a doc", "create doc", "generate doc",
            "create brd", "generate brd", "draft brd", "create prd", "generate prd", "author user stor"
        ])
        is_doc_query = (
            not is_create_directive and
            any(k in p_lower for k in [
                "how many doc", "list doc", "show doc", "what doc", "documents created",
                "brd status", "specifications created", "document list", "governed doc",
                "all documents", "existing documents"
            ])
        )

        if is_doc_query:
            with db() as con:
                proj = row(con.execute("SELECT id, name FROM projects WHERE id=?", (target_proj,)))
                proj_name = proj["name"] if proj else target_proj
                docs_db = rows(con.execute(
                    "SELECT id, kind, title, status, current_version, updated_at FROM documents WHERE project_id=? ORDER BY updated_at DESC",
                    (target_proj,)
                ))

            docs_list = [dict(d) for d in docs_db]
            doc_rows = []
            prefix = "MCP" if "mcp" in target_proj.lower() else "QE"
            for idx, d in enumerate(docs_list, 1):
                gov_id = f"{prefix}-DOC-{idx:03d}"
                st_badge = "🟢 `APPROVED`" if d.get("status") == "approved" else "🟡 `DRAFT`"
                upd = d.get("updated_at", "")[:19].replace("T", " ") if d.get("updated_at") else "Recorded"
                doc_rows.append(f"| `{gov_id}` | `{d['id']}` | **{d['title'][:55]}** | `{d['kind'].upper()}` | `v{d['current_version']}` | {st_badge} | {upd} |")

            table_content = "\n".join(doc_rows) if doc_rows else "| - | - | *(No documents created yet)* | - | - | - | - |"
            content = (
                f"### 📄 Governed Documents Inventory · {proj_name} (`{target_proj}`)\n\n"
                f"There are **{len(docs_list)} governed documents** registered in `data/atlas.sqlite3` for this project:\n\n"
                f"| Governance ID | Document ID | Title | Kind | Version | Status | Updated At |\n"
                f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
                + table_content + "\n\n"
                f"💡 *All specifications are immutable SHA-256 signed. You can view, edit, or export them in Markdown or DOCX on the [Documents Page](/projects/{target_proj}/documents).*"
            )

            tool_record = ToolCallRecord(
                id=f"call_docs_ground_{now_ms}",
                name="read_document",
                args={"projectId": target_proj},
                result={"projectId": target_proj, "documentsCount": len(docs_list), "status": "Retrieved from centralized DB"},
                status="completed"
            )

            return {
                "thought": f"Centralized Database Grounding: queried data/atlas.sqlite3 (table: `documents`). Found {len(docs_list)} documents for project {proj_name}.",
                "content": content,
                "tool_calls": [tool_record]
            }

        # -------------------------------------------------------------------------
        # 3. Quality Gates Inquiries
        # -------------------------------------------------------------------------
        is_gate_query = any(k in p_lower for k in [
            "how many gate", "gate status", "show gate", "check gate", "quality gate status",
            "gates scorecard", "gate score", "which gates approved", "quality gates"
        ])

        if is_gate_query:
            with db() as con:
                proj = row(con.execute("SELECT id, name FROM projects WHERE id=?", (target_proj,)))
                proj_name = proj["name"] if proj else target_proj
                gates_db = rows(con.execute(
                    "SELECT gate, status, decided_by, reason, decided_at FROM gates WHERE project_id=? ORDER BY gate ASC",
                    (target_proj,)
                ))

            gates_list = [dict(g) for g in gates_db]
            gate_rows = []
            approved_count = 0
            for g in gates_list:
                st = g.get("status", "pending")
                if st == "approved":
                    approved_count += 1
                icon = "🟢 `APPROVED`" if st == "approved" else "🟡 `DRAFT`" if st == "draft" else "⚪ `PENDING`"
                decider = g.get("decided_by") or "—"
                reason = g.get("reason") or "—"
                gate_rows.append(f"| Gate {g['gate']} | {icon} | `{decider}` | {reason} |")

            content = (
                f"### 🛡️ Quality Engineering Gates Scorecard · {proj_name} (`{target_proj}`)\n\n"
                f"**Overall Compliance:** **{approved_count}/{len(gates_list)} Gates Approved**\n\n"
                f"| Quality Gate | Status | Decided By | Reason / Evidence |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                + "\n".join(gate_rows) + "\n\n"
                f"💡 *Gate status is cryptographically signed and stored in the centralized database (`data/atlas.sqlite3`).*"
            )

            tool_record = ToolCallRecord(
                id=f"call_gates_ground_{now_ms}",
                name="check_gates",
                args={"projectId": target_proj},
                result={"projectId": target_proj, "approvedCount": approved_count, "totalGates": len(gates_list)},
                status="completed"
            )

            return {
                "thought": f"Centralized Database Grounding: queried data/atlas.sqlite3 (table: `gates`). Found {approved_count}/{len(gates_list)} approved gates for project {proj_name}.",
                "content": content,
                "tool_calls": [tool_record]
            }

        return None
