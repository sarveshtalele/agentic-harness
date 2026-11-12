"use client";

import { useEffect, useState, useMemo } from "react";
import { AppShell } from "../../components/AppShell";
import { ConfirmModal, Empty, ErrorNote, PageTitle, Spinner, useToast } from "../../components/ui";
import { useAuth } from "../../components/AuthGate";
import { api } from "../../lib/api";
import { SkillItem } from "../../features/skills/lib";
import { SkillCard } from "../../features/skills/SkillCard";
import { SkillFilters } from "../../features/skills/SkillFilters";
import { SkillModal } from "../../features/skills/SkillModal";

export default function SkillsPage() {
  const [data, setData] = useState<{ skills: SkillItem[]; problems: string[] } | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillItem | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("all");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/skills")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const toast = useToast();
  const admin = useAuth().user?.role === "admin";
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([]);
  const [ledgerProject, setLedgerProject] = useState("");
  useEffect(() => {
    if (admin) api("/projects").then((r) => setProjects(Array.isArray(r) ? r : r.projects)).catch((e) => setError(e.message));
  }, [admin]);
  const [confirmDeleteSkill, setConfirmDeleteSkill] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openSkillModal = async (skill: SkillItem) => {
    setSelectedSkill(skill);
    setLoadingDetail(true);
    setDetail(null);
    try {
      const res = await api(`/skills/${skill.name}`);
      setDetail(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const closeModal = () => {
    setSelectedSkill(null);
    setDetail(null);
  };

  const handleRecheck = async (skillName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const health = await api<SkillItem["health"]>(`/skills/${encodeURIComponent(skillName)}/health`, { method: "POST" });
      setData((prev) => prev ? { ...prev, skills: prev.skills.map((s) => s.name === skillName ? { ...s, health } : s) } : null);
      toast(health?.verdict === "ok" ? `Skill '${skillName}' can run here` : `Skill '${skillName}': ${health?.verdict}`, health?.verdict === "ok" ? "ok" : "error");
    } catch (err) {
      toast(`Could not check '${skillName}': ${(err as Error).message}`, "error");
    }
  };

  const handleDeleteSkill = (skillName: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setConfirmDeleteSkill(skillName);
  };

  const handleConfirmDelete = async () => {
    if (!confirmDeleteSkill) return;
    if (!ledgerProject) { toast("Choose the project that records this deletion first", "error"); setConfirmDeleteSkill(null); return; }
    const skillName = confirmDeleteSkill;
    setDeleting(true);
    try {
      await api(`/skill-studio/skills/${encodeURIComponent(skillName)}?project_id=${encodeURIComponent(ledgerProject)}`, { method: "DELETE" });
      setData((prev) => prev ? { ...prev, skills: prev.skills.filter(s => s.name !== skillName) } : null);
      if (selectedSkill?.name === skillName) {
        closeModal();
      }
      try {
        const stored = JSON.parse(localStorage.getItem("aqe_deleted_skills") || "[]");
        if (!stored.includes(skillName)) {
          stored.push(skillName);
          localStorage.setItem("aqe_deleted_skills", JSON.stringify(stored));
        }
        window.dispatchEvent(new CustomEvent("aqe:skill_deleted", { detail: { slug: skillName } }));
      } catch {}
      toast(`Skill '${skillName}' deleted (its versions are kept)`, "ok");
    } catch (err: any) {
      toast(`Failed to delete skill: ${err.message}`, "error");
    } finally {
      setDeleting(false);
      setConfirmDeleteSkill(null);
    }
  };

  const allAgents = useMemo(() => {
    if (!data?.skills) return [];
    const set = new Set<string>();
    data.skills.forEach(s => s.agents.forEach(a => set.add(a)));
    return Array.from(set);
  }, [data]);

  const filteredSkills = useMemo(() => {
    if (!data?.skills) return [];
    return data.skills.filter(s => {
      const matchesSearch = s.name.toLowerCase().includes(search.toLowerCase()) || 
                            s.description.toLowerCase().includes(search.toLowerCase());
      const matchesAgent = selectedAgent === "all" || s.agents.includes(selectedAgent);
      return matchesSearch && matchesAgent;
    });
  }, [data, search, selectedAgent]);

  return (
    <AppShell>
      <PageTitle 
        title="Skills & Tool Catalog" 
        subtitle="Skills loaded by Microsoft Agent Framework from skills/ and plugins, with their content hash. Agents load them on demand."
      />
      <ErrorNote message={error} />

      {admin && (
        <label className="mb-3 flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
          Record deletions in project
          <select aria-label="Project for deletions" data-testid="skills-ledger-project" value={ledgerProject} onChange={(e) => setLedgerProject(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-2 py-1 dark:border-slate-700 dark:bg-[#070d1f]">
            <option value="">Choose a project</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </label>
      )}

      {/* Filter and Search Bar */}
      <SkillFilters search={search} setSearch={setSearch} selectedAgent={selectedAgent} setSelectedAgent={setSelectedAgent} allAgents={allAgents} total={data?.skills.length || 0} />

      {!data ? (
        !error && <Spinner />
      ) : (
        <>
          {data.problems.map((p) => (
            <p key={p} role="alert" className="mb-3 text-xs text-rose-500 font-mono">
              ⚠️ {p}
            </p>
          ))}

          {filteredSkills.length === 0 ? (
            <Empty title="No skills found matching your filter criteria" />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="skill-cards-grid">
              {filteredSkills.map((s) => (
                <SkillCard key={s.name} s={s} onOpen={() => openSkillModal(s)} onDelete={admin ? (e) => handleDeleteSkill(s.name, e) : undefined}
                  onRecheck={admin ? (e) => handleRecheck(s.name, e) : undefined} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Skill Detail & Code Preview Modal */}
      {selectedSkill && (
        <SkillModal selectedSkill={selectedSkill} detail={detail} loadingDetail={loadingDetail} onClose={closeModal} onDelete={admin ? () => handleDeleteSkill(selectedSkill.name) : undefined} />
      )}

      <ConfirmModal
        open={!!confirmDeleteSkill}
        title="Delete Agent Skill"
        message={`Are you sure you want to delete skill '${confirmDeleteSkill}'? The installed folder is removed; its published versions stay in the database.`}
        confirmLabel="Delete Skill"
        variant="danger"
        busy={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!deleting) setConfirmDeleteSkill(null);
        }}
      />
    </AppShell>
  );
}
