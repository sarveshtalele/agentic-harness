"use client";

import React, { useState, useEffect } from "react";
import { Wrench, Search, Shield, Cpu, ChevronRight } from "lucide-react";
import { Badge } from "../ui/Badge";

interface ToolItem {
  name: string;
  description: string;
  parameters: any;
  requiresApproval: boolean;
  gateNumber?: number;
  category?: string;
}

export const MCPToolsExplorer: React.FC = () => {
  const [tools, setTools] = useState<ToolItem[]>([]);
  const [search, setSearch] = useState("");
  const [selectedTool, setSelectedTool] = useState<ToolItem | null>(null);

  useEffect(() => {
    fetch("/api/tools")
      .then((res) => res.json())
      .then((data) => {
        if (data.tools) setTools(data.tools);
      })
      .catch((err) => console.error("Failed to fetch tools:", err));
  }, []);

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col h-full text-xs font-mono">
      {/* Search Header */}
      <div className="p-3 border-b border-zinc-800 space-y-2">
        <div className="flex items-center gap-1.5 font-semibold text-zinc-200">
          <Wrench className="w-4 h-4 text-indigo-400" />
          <span>Tools & MCP Registry</span>
          <Badge variant="outline" size="sm" className="ml-auto">
            {tools.length} Loaded
          </Badge>
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tools, gates, schemas..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded pl-8 pr-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Tools List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filtered.map((tool) => (
          <div
            key={tool.name}
            onClick={() => setSelectedTool(selectedTool?.name === tool.name ? null : tool)}
            className="p-2.5 rounded border border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between gap-1">
              <span className="font-semibold text-zinc-200">{tool.name}</span>
              {tool.gateNumber ? (
                <Badge variant="purple" size="sm">Gate {tool.gateNumber}</Badge>
              ) : (
                <Badge variant="outline" size="sm">{tool.category || "Tool"}</Badge>
              )}
            </div>
            <p className="text-[11px] text-zinc-400 font-sans mt-1 line-clamp-2">
              {tool.description}
            </p>

            {selectedTool?.name === tool.name && (
              <div className="mt-2.5 pt-2 border-t border-zinc-800 text-[10px] space-y-1.5">
                <div className="text-zinc-500">Parameters Schema:</div>
                <pre className="bg-black/50 p-2 rounded border border-zinc-800 text-zinc-300 overflow-x-auto max-h-36">
                  {JSON.stringify(tool.parameters, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
