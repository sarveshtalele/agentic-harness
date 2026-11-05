"use client";

import React, { useState, useEffect } from "react";
import { X, Server, Plus, CheckCircle, AlertCircle, RefreshCw, Terminal, Globe } from "lucide-react";
import { MCPServerConfig } from "@/lib/maf/types";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

interface MCPSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MCPSettingsModal: React.FC<MCPSettingsModalProps> = ({ isOpen, onClose }) => {
  const [servers, setServers] = useState<MCPServerConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [transport, setTransport] = useState<"stdio" | "sse">("stdio");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [sseUrl, setSseUrl] = useState("");

  const fetchServers = () => {
    setLoading(true);
    fetch("/api/mcp")
      .then((r) => r.json())
      .then((d) => {
        if (d.servers) setServers(d.servers);
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) {
      fetchServers();
    }
  }, [isOpen]);

  const handleAddServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const parsedArgs = args
        .split(" ")
        .map((a) => a.trim())
        .filter(Boolean);

      const res = await fetch("/api/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          transport,
          command: command.trim() || undefined,
          args: parsedArgs.length > 0 ? parsedArgs : undefined,
          sseUrl: sseUrl.trim() || undefined,
        }),
      });

      if (res.ok) {
        setShowAddForm(false);
        setName("");
        setCommand("");
        setArgs("");
        setSseUrl("");
        fetchServers();
      }
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl max-w-xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden text-xs">
        {/* Header */}
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-zinc-100 text-sm">Model Context Protocol (MCP) Hub</h3>
              <p className="text-[11px] text-zinc-500 font-mono">Connect stdio & SSE tools to MAF agents</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 flex-1 overflow-y-auto space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-zinc-400 uppercase tracking-wider text-[11px]">
              Configured MCP Servers ({servers.length})
            </span>
            <Button
              variant="secondary"
              size="xs"
              onClick={() => setShowAddForm(!showAddForm)}
              className="gap-1 font-mono"
            >
              <Plus className="w-3 h-3" /> Add Server
            </Button>
          </div>

          {/* Add Server Form */}
          {showAddForm && (
            <form onSubmit={handleAddServer} className="p-3 rounded-lg border border-indigo-500/40 bg-zinc-900/80 space-y-3">
              <div className="flex items-center justify-between font-mono text-[11px] text-indigo-300">
                <span>New MCP Server Connection</span>
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="text-zinc-500 hover:text-zinc-300"
                >
                  Cancel
                </button>
              </div>

              <div>
                <label className="text-zinc-400 text-[11px] block mb-1">Server Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Postgres DB MCP or GitHub Tools"
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="flex gap-4">
                <label className="flex items-center gap-1.5 text-zinc-300 cursor-pointer">
                  <input
                    type="radio"
                    name="transport"
                    checked={transport === "stdio"}
                    onChange={() => setTransport("stdio")}
                    className="accent-indigo-500"
                  />
                  <span>stdio (CLI subprocess)</span>
                </label>
                <label className="flex items-center gap-1.5 text-zinc-300 cursor-pointer">
                  <input
                    type="radio"
                    name="transport"
                    checked={transport === "sse"}
                    onChange={() => setTransport("sse")}
                    className="accent-indigo-500"
                  />
                  <span>SSE (Remote HTTP URL)</span>
                </label>
              </div>

              {transport === "stdio" ? (
                <>
                  <div>
                    <label className="text-zinc-400 text-[11px] block mb-1">Command</label>
                    <input
                      type="text"
                      value={command}
                      onChange={(e) => setCommand(e.target.value)}
                      placeholder="e.g. npx or python"
                      className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 font-mono focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 text-[11px] block mb-1">Arguments</label>
                    <input
                      type="text"
                      value={args}
                      onChange={(e) => setArgs(e.target.value)}
                      placeholder="-y @modelcontextprotocol/server-postgres postgresql://..."
                      className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 font-mono focus:outline-none"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="text-zinc-400 text-[11px] block mb-1">SSE Endpoint URL</label>
                  <input
                    type="url"
                    value={sseUrl}
                    onChange={(e) => setSseUrl(e.target.value)}
                    placeholder="https://mcp-server.domain.com/sse"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-zinc-200 font-mono focus:outline-none"
                  />
                </div>
              )}

              <div className="flex justify-end pt-1">
                <Button type="submit" variant="primary" size="sm">
                  Save & Connect
                </Button>
              </div>
            </form>
          )}

          {/* Servers list */}
          <div className="space-y-2">
            {servers.map((srv) => (
              <div
                key={srv.id}
                className="p-3 rounded-lg border border-zinc-800 bg-zinc-900/60 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-zinc-800/80 text-zinc-300">
                    {srv.transport === "stdio" ? (
                      <Terminal className="w-4 h-4 text-indigo-400" />
                    ) : (
                      <Globe className="w-4 h-4 text-emerald-400" />
                    )}
                  </div>
                  <div>
                    <h4 className="font-semibold text-zinc-100">{srv.name}</h4>
                    <p className="text-[11px] text-zinc-500 font-mono mt-0.5">
                      {srv.transport.toUpperCase()} · {srv.toolsCount || 0} tools exposed
                    </p>
                  </div>
                </div>

                <Badge
                  variant={srv.status === "connected" ? "success" : "outline"}
                  size="sm"
                  className="gap-1"
                >
                  {srv.status === "connected" ? (
                    <>
                      <CheckCircle className="w-2.5 h-2.5" /> connected
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-2.5 h-2.5" /> {srv.status}
                    </>
                  )}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-zinc-800 flex justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};
