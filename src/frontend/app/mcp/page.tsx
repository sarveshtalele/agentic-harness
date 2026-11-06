"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { AppShell } from "../../components/AppShell";
import { Badge, Button, Empty, ErrorNote, PageTitle, Spinner } from "../../components/ui";
import { ConfirmModal } from "../../components/ConfirmModal";
import { api } from "../../lib/api";
import {
  Cpu,
  Plus,
  Search,
  Check,
  Copy,
  Terminal,
  Globe,
  Sliders,
  X,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Code2,
  ChevronRight,
  ExternalLink,
  Shield,
  Layers,
  Wrench,
  ToggleLeft,
  ToggleRight,
  Play
} from "lucide-react";

interface MCPTool {
  id: string;
  server_id: string;
  name: string;
  description: string;
  parameters_schema: any;
  authorized: boolean;
  created_at: string;
  updated_at: string;
}

interface MCPServer {
  id: string;
  name: string;
  type: string;
  transport: string;
  command: string | null;
  url: string | null;
  status: "connected" | "error" | "disabled" | "disconnected" | string;
  error_message?: string;
  total_tools: number;
  authorized_tools: number;
  tools_count?: number;
  tools: MCPTool[];
  created_at: string;
  updated_at: string;
}

export default function MCPPage() {
  const [servers, setServers] = useState<MCPServer[] | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Modals state
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [connectTab, setConnectTab] = useState<"local" | "remote">("remote");
  const [busyAction, setBusyAction] = useState(false);

  // Connect form state
  const [serverName, setServerName] = useState("");
  const [serverUrl, setServerUrl] = useState("");
  const [serverTransport, setServerTransport] = useState("sse");
  const [serverCommand, setServerCommand] = useState("");
  const [connectError, setConnectError] = useState("");

  // Tool search inside modal
  const [toolSearch, setToolSearch] = useState("");
  const [serverToDelete, setServerToDelete] = useState<MCPServer | null>(null);

  const loadServers = useCallback(async () => {
    try {
      const res = await api("/mcp/servers");
      setServers(res.servers || []);
    } catch (e: any) {
      setError(e.message || "Failed to load MCP servers");
    }
  }, []);

  useEffect(() => {
    loadServers();
  }, [loadServers]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleToggleAll = async (server: MCPServer) => {
    try {
      const allAuth = server.authorized_tools === server.total_tools;
      const res = await api(`/mcp/servers/${server.id}/toggle-all`, {
        method: "POST",
        json: { authorized: !allAuth },
      });
      loadServers();
      if (selectedServer?.id === server.id) {
        setSelectedServer((prev) => (prev ? { ...prev, ...res.server } : null));
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleToggleTool = async (tool: MCPTool) => {
    try {
      const res = await api(`/mcp/tools/${tool.id}/toggle`, {
        method: "POST",
        json: { authorized: !tool.authorized },
      });
      loadServers();
      if (selectedServer) {
        setSelectedServer((prev) => {
          if (!prev) return null;
          const updated = prev.tools.map((t) => (t.id === tool.id ? { ...t, ...res.tool } : t));
          const authCount = updated.filter((t) => t.authorized).length;
          return { ...prev, tools: updated, authorized_tools: authCount };
        });
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDeleteServer = (server: MCPServer) => {
    setServerToDelete(server);
  };

  const executeDeleteServer = async () => {
    if (!serverToDelete) return;
    try {
      await api(`/mcp/servers/${serverToDelete.id}`, { method: "DELETE" });
      if (selectedServer?.id === serverToDelete.id) setSelectedServer(null);
      setServerToDelete(null);
      loadServers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleConnectServer = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnectError("");
    setBusyAction(true);
    try {
      const payload: any = {
        name: serverName.trim(),
        type: connectTab === "local" ? "local_npx" : "remote_sse",
      };
      if (connectTab === "local") {
        payload.command = serverCommand.trim();
        payload.transport = "stdio";
      } else {
        payload.url = serverUrl.trim();
        payload.transport = serverTransport;
      }

      await api("/mcp/servers", {
        method: "POST",
        json: payload,
      });

      setShowConnectModal(false);
      setServerName("");
      setServerUrl("");
      setServerCommand("");
      loadServers();
    } catch (err: any) {
      setConnectError(err.message || "Failed to connect MCP server");
    } finally {
      setBusyAction(false);
    }
  };

  const stats = useMemo(() => {
    if (!servers) return [];
    const totalServers = servers.length;
    const connectedServers = servers.filter((s) => s.status === "connected").length;
    const totalTools = servers.reduce((acc, s) => acc + s.total_tools, 0);
    const authorizedTools = servers.reduce((acc, s) => acc + s.authorized_tools, 0);
    return [
      ["Total Servers", totalServers],
      ["Connected Servers", connectedServers],
      ["Total Tools", totalTools],
      ["Authorized Tools", authorizedTools],
    ];
  }, [servers]);

  const filteredServers = useMemo(() => {
    if (!servers) return [];
    return servers.filter((s) => {
      const q = search.toLowerCase();
      const matchesSearch =
        s.name.toLowerCase().includes(q) ||
        (s.command && s.command.toLowerCase().includes(q)) ||
        (s.url && s.url.toLowerCase().includes(q));
      const isLocal = s.type === "local_npx" || s.type === "local";
      const matchesType =
        selectedType === "all" ||
        (selectedType === "local" && isLocal) ||
        (selectedType === "remote" && !isLocal);
      return matchesSearch && matchesType;
    });
  }, [servers, search, selectedType]);

  const filteredModalTools = useMemo(() => {
    if (!selectedServer) return [];
    const q = toolSearch.toLowerCase();
    return selectedServer.tools.filter(
      (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    );
  }, [selectedServer, toolSearch]);

  const getTypeBadge = (type: string) => {
    const isLocal = type === "local_npx" || type === "local";
    if (isLocal) {
      return (
        <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <Terminal className="h-3 w-3" /> Local NPX
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded-md bg-indigo-500/10 px-2 py-0.5 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
        <Globe className="h-3 w-3" /> Remote SSE
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "connected":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Connected
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-bold text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
            Error
          </span>
        );
      case "disabled":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
            Disabled
          </span>
        );
    }
  };

  return (
    <AppShell>
      <PageTitle
        title="Model Context Protocol (MCP) Servers"
        subtitle="Connect, manage, and authorize local NPX tools and remote SSE/HTTP MCP servers with runtime sandboxing."
        actions={
          <Button
            data-testid="connect-mcp-btn"
            onClick={() => {
              setConnectError("");
              setShowConnectModal(true);
            }}
          >
            <Plus className="h-4 w-4" /> Connect MCP Server
          </Button>
        }
      />

      <ErrorNote message={error} />

      {/* Header with Stats Grid */}
      <dl className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="mcp-stats">
        {stats.map(([k, v]) => (
          <div
            key={k as string}
            className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-[#0b1329]"
          >
            <dd className="text-2xl font-bold text-slate-900 dark:text-white">{v}</dd>
            <dt className="text-xs text-slate-500 font-medium mt-1">{k}</dt>
          </div>
        ))}
      </dl>

      {/* Filter and Search Bar */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search MCP servers by name, command, or endpoint URL..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 flex items-center gap-1 font-medium">
            <Sliders className="h-3.5 w-3.5" /> Type:
          </span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold outline-none transition focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
          >
            <option value="all">All Server Types</option>
            <option value="local">Local NPX Servers</option>
            <option value="remote">Remote SSE Servers</option>
          </select>
        </div>
      </div>

      {!servers ? (
        !error && <Spinner label="Loading MCP registry..." />
      ) : filteredServers.length === 0 ? (
        <Empty title="No MCP servers match your criteria">
          <Button
            variant="secondary"
            className="mt-3"
            onClick={() => {
              setSearch("");
              setSelectedType("all");
            }}
          >
            Clear Filters
          </Button>
        </Empty>
      ) : (
        /* 3-Column Card Grid */
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="mcp-servers-grid">
          {filteredServers.map((server) => {
            const allAuth = server.authorized_tools === server.total_tools && server.total_tools > 0;
            const commandOrUrl = server.command || server.url || "";
            const isCopied = copiedId === server.id;

            return (
              <div
                key={server.id}
                data-testid="mcp-server-card"
                className="group relative flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 transition-all hover:border-indigo-500 hover:shadow-md dark:border-slate-800 dark:bg-[#0b1329]"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
                        <Cpu className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="font-bold text-sm text-slate-900 group-hover:text-indigo-600 dark:text-slate-100 dark:group-hover:text-indigo-400 transition">
                          {server.name}
                        </h3>
                        <div className="mt-1 flex items-center gap-1.5">
                          {getTypeBadge(server.type)}
                        </div>
                      </div>
                    </div>
                    <div>{getStatusBadge(server.status)}</div>
                  </div>

                  {/* URL / Command Box with Copy Button */}
                  <div className="mt-4 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-mono text-xs dark:border-slate-800 dark:bg-slate-900/60">
                    <span className="truncate text-slate-700 dark:text-slate-300 pr-2 select-all" title={commandOrUrl}>
                      {commandOrUrl}
                    </span>
                    <button
                      onClick={() => copyToClipboard(commandOrUrl, server.id)}
                      title={isCopied ? "Copied!" : "Copy command or URL"}
                      className="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
                    >
                      {isCopied ? (
                        <Check className="h-3.5 w-3.5 text-emerald-500" />
                      ) : (
                        <Copy className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>

                  {/* Metrics and Status */}
                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800/80">
                    <div>
                      <span className="text-[11px] font-medium text-slate-500">Authorized Tools:</span>
                      <div className="mt-0.5 flex items-center gap-1.5">
                        <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          {server.authorized_tools} / {server.total_tools}
                        </span>
                        <span className="text-[11px] text-slate-400">active</span>
                      </div>
                    </div>

                    <div className="text-right">
                      <span className="text-[11px] font-medium text-slate-500">Transport:</span>
                      <div className="mt-0.5 font-mono text-xs font-semibold uppercase text-slate-700 dark:text-slate-300">
                        {server.transport || "stdio"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Card Actions Footer */}
                <div className="mt-5 space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                  <div className="flex items-center gap-2">
                    {/* Master Toggle */}
                    <button
                      onClick={() => handleToggleAll(server)}
                      className={`flex-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition border ${
                        allAuth
                          ? "border-rose-500/30 bg-rose-500/10 text-rose-600 hover:bg-rose-500/20 dark:text-rose-400"
                          : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
                      }`}
                    >
                      {allAuth ? "Disable All Tools" : "Authorize All Tools"}
                    </button>

                    {/* Delete button */}
                    <button
                      onClick={() => handleDeleteServer(server)}
                      title="Delete Server"
                      className="rounded-lg border border-slate-200 p-1.5 text-slate-400 hover:border-rose-500 hover:text-rose-600 dark:border-slate-800 dark:hover:border-rose-500 transition"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  {/* View & Manage Tools Button */}
                  <Button
                    variant="secondary"
                    className="w-full text-xs"
                    onClick={() => {
                      setToolSearch("");
                      setSelectedServer(server);
                    }}
                  >
                    <Wrench className="h-3.5 w-3.5 text-indigo-500" /> View & Manage Tools ({server.total_tools})
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. VIEW & MANAGE TOOLS MODAL / DRAWER */}
      {/* ========================================================================= */}
      {selectedServer && (
        <div
          data-testid="tools-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm"
        >
          <div className="flex h-full max-h-[85vh] w-full max-w-3xl flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-[#070e24]">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-indigo-600/10 p-2 text-indigo-600 dark:text-indigo-400">
                  <Cpu className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-slate-900 dark:text-white">
                      {selectedServer.name}
                    </h2>
                    {getTypeBadge(selectedServer.type)}
                  </div>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    {selectedServer.command || selectedServer.url}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setSelectedServer(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Subheader Controls */}
            <div className="flex flex-col gap-3 border-b border-slate-100 bg-slate-50/50 px-6 py-3 dark:border-slate-800/60 dark:bg-slate-900/40 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter discovered tools..."
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs outline-none focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
                />
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-3">
                <span className="text-xs text-slate-500">
                  <b>{selectedServer.authorized_tools}</b> of <b>{selectedServer.total_tools}</b> Authorized
                </span>
                <button
                  onClick={() => handleToggleAll(selectedServer)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition border ${
                    selectedServer.authorized_tools === selectedServer.total_tools
                      ? "border-rose-500/30 bg-rose-500/10 text-rose-600 hover:bg-rose-500/20 dark:text-rose-400"
                      : "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400"
                  }`}
                >
                  {selectedServer.authorized_tools === selectedServer.total_tools
                    ? "Disable All"
                    : "Authorize All"}
                </button>
              </div>
            </div>

            {/* Tools List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {filteredModalTools.length === 0 ? (
                <Empty title="No tools match your query" />
              ) : (
                filteredModalTools.map((tool) => (
                  <div
                    key={tool.id}
                    data-testid="tool-item"
                    className="rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-[#0b1329]"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-slate-900 dark:text-slate-100">
                            {tool.name}
                          </span>
                          <span
                            className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-bold ${
                              tool.authorized
                                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30"
                                : "bg-rose-500/15 text-rose-700 dark:text-rose-400 border border-rose-500/30"
                            }`}
                          >
                            {tool.authorized ? "Authorized" : "Disabled"}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                          {tool.description || "No description provided."}
                        </p>
                      </div>

                      {/* Tool Authorization Toggle Switch */}
                      <button
                        onClick={() => handleToggleTool(tool)}
                        title={tool.authorized ? "Disable tool" : "Authorize tool"}
                        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                          tool.authorized ? "bg-emerald-600" : "bg-slate-300 dark:bg-slate-700"
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                            tool.authorized ? "translate-x-5" : "translate-x-0"
                          }`}
                        />
                      </button>
                    </div>

                    {/* JSON Schema Preview */}
                    <div className="mt-3">
                      <details className="group">
                        <summary className="flex cursor-pointer items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400">
                          <Code2 className="h-3.5 w-3.5" />
                          <span>View JSON Parameters Schema</span>
                        </summary>
                        <pre className="mt-2 max-h-48 overflow-x-auto rounded-lg bg-slate-950 p-3 font-mono text-[11px] text-slate-300">
                          {JSON.stringify(tool.parameters_schema || {}, null, 2)}
                        </pre>
                      </details>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end border-t border-slate-200 px-6 py-3 dark:border-slate-800">
              <Button variant="secondary" onClick={() => setSelectedServer(null)}>
                Done
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. CONNECT MCP SERVER MODAL (Remote SSE / Local NPX) */}
      {/* ========================================================================= */}
      {showConnectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-[#070e24]">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="rounded-lg bg-indigo-600/10 p-2 text-indigo-600 dark:text-indigo-400">
                  <Cpu className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">
                    Connect MCP Server
                  </h2>
                  <p className="text-xs text-slate-500">
                    Register a Model Context Protocol server and auto-discover tools.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowConnectModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {connectError && (
              <div className="mt-4 rounded-lg border border-rose-500/40 bg-rose-500/10 p-2.5 text-xs text-rose-600 dark:text-rose-400">
                {connectError}
              </div>
            )}

            {/* Tab Switcher: Remote MCP Server (SSE/HTTP) vs Local NPX */}
            <div className="mt-4 flex rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-800 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => setConnectTab("remote")}
                className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition ${
                  connectTab === "remote"
                    ? "bg-white text-indigo-600 shadow-sm dark:bg-indigo-600 dark:text-white"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                }`}
              >
                <Globe className="h-3.5 w-3.5" /> Remote MCP Server (SSE)
              </button>
              <button
                type="button"
                onClick={() => setConnectTab("local")}
                className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-semibold transition ${
                  connectTab === "local"
                    ? "bg-white text-indigo-600 shadow-sm dark:bg-indigo-600 dark:text-white"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400"
                }`}
              >
                <Terminal className="h-3.5 w-3.5" /> Local NPX Server
              </button>
            </div>

            <form onSubmit={handleConnectServer} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Server Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder={
                    connectTab === "remote" ? "e.g. GitHub Copilot MCP" : "e.g. SQLite Database MCP"
                  }
                  value={serverName}
                  onChange={(e) => setServerName(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
                />
              </div>

              {connectTab === "remote" ? (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Remote Endpoint URL (SSE / HTTP) *
                    </label>
                    <input
                      type="url"
                      required
                      placeholder="https://api.example.com/mcp/sse"
                      value={serverUrl}
                      onChange={(e) => setServerUrl(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-mono outline-none transition focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Transport Protocol
                    </label>
                    <select
                      value={serverTransport}
                      onChange={(e) => setServerTransport(e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium outline-none transition focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
                    >
                      <option value="sse">Server-Sent Events (SSE)</option>
                      <option value="http">HTTP Streaming</option>
                    </select>
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    NPX Launch Command *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="npx -y @modelcontextprotocol/server-sqlite --db data.db"
                    value={serverCommand}
                    onChange={(e) => setServerCommand(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-mono outline-none transition focus:border-indigo-500 dark:border-slate-800 dark:bg-[#0b1329]"
                  />
                  <span className="mt-1 block text-[11px] text-slate-500">
                    Command runs inside sandboxed subprocess. Must begin with <code>npx</code> or <code>node</code>.
                  </span>
                </div>
              )}

              {/* Quick Presets */}
              <div>
                <span className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                  Popular Presets
                </span>
                <div className="flex flex-wrap gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setConnectTab("local");
                      setServerName("SQLite Database MCP");
                      setServerCommand("npx -y @modelcontextprotocol/server-sqlite --db database.db");
                    }}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-mono hover:border-indigo-500 dark:border-slate-800 dark:bg-slate-900"
                  >
                    SQLite Local
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setConnectTab("local");
                      setServerName("Playwright MCP");
                      setServerCommand("npx -y @executeautomation/playwright-mcp-server");
                    }}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-mono hover:border-indigo-500 dark:border-slate-800 dark:bg-slate-900"
                  >
                    Playwright Local
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setConnectTab("remote");
                      setServerName("GitHub Copilot MCP");
                      setServerUrl("https://api.githubcopilot.com/mcp");
                      setServerTransport("sse");
                    }}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2 py-1 text-[11px] font-mono hover:border-indigo-500 dark:border-slate-800 dark:bg-slate-900"
                  >
                    GitHub Remote
                  </button>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setShowConnectModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" busy={busyAction}>
                  Connect Server
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Confirmation Modal for Server Deletion */}
      <ConfirmModal
        isOpen={!!serverToDelete}
        title="Delete MCP Server"
        description={`Are you sure you want to permanently delete MCP server "${serverToDelete?.name}"? All discovered tools will be disconnected.`}
        tone="danger"
        confirmText="Delete Server"
        onConfirm={executeDeleteServer}
        onClose={() => setServerToDelete(null)}
      />
    </AppShell>
  );
}
