/** Shapes of /api/capabilities (backend/core/registry). */
export interface Capability {
  id: string;
  kind: string;
  name: string;
  qualified_name: string;
  description: string;
  when_to_use?: string;
  source?: string;
  plugin?: string | null;
  risk: string;
  needs_approval: boolean;
  profiles?: string;
  enabled: boolean;
  sha256?: string;
  updated_at?: string;
  meta?: Record<string, unknown>;
}

export interface Version { id: number; hash: string; capabilities: number; links: number; problems: string[]; synced_by: string; synced_at: string }

export interface Linked extends Capability { relation: string; detail: string }

export interface Detail extends Capability { up: Linked[]; down: Linked[] }

export interface TreeNode extends Capability { relation: string; children: TreeNode[] }
