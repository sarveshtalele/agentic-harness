export interface SkillItem {
  name: string;
  description: string;
  version: string;
  agents: string[];
  chars: number;
  references: string[];
  sha256: string;
  health?: { verdict: "ok" | "warning" | "flagged"; reason: string };
}
