"use client";

import { Badge } from "../../components/ui";
import { TreeNode } from "./types";

function Node({ node, onOpen }: { node: TreeNode; onOpen: (id: string) => void }) {
  const label = (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {node.relation && <span className="text-[10px] uppercase tracking-wide text-slate-400">{node.relation.replace("_", " ")}</span>}
      <Badge tone="indigo">{node.kind}</Badge>
      <button type="button" className="mono text-left text-indigo-600 underline dark:text-indigo-400" onClick={(e) => { e.preventDefault(); onOpen(node.id); }}>{node.qualified_name}</button>
      {node.needs_approval && <Badge tone="amber">needs approval</Badge>}
      {!node.enabled && <Badge tone="slate">disabled</Badge>}
    </span>
  );
  if (!node.children.length) return <li className="py-0.5 pl-4">{label}</li>;
  return (
    <li className="py-0.5">
      <details>
        <summary className="cursor-pointer">{label} <span className="text-slate-400">({node.children.length})</span></summary>
        <ul className="ml-3 border-l border-slate-200 pl-2 dark:border-slate-800">
          {node.children.map((child) => <Node key={`${child.relation}-${child.id}`} node={child} onOpen={onOpen} />)}
        </ul>
      </details>
    </li>
  );
}

/** Plugin → commands, skills, agents, hooks, scripts; workflow → stages → agents → tools and skills; MCP server → tools. */
export function CapTree({ roots, onOpen }: { roots: TreeNode[]; onOpen: (id: string) => void }) {
  return (
    <ul className="rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800" data-testid="capabilities-tree">
      {roots.map((root) => <Node key={root.id} node={root} onOpen={onOpen} />)}
    </ul>
  );
}
