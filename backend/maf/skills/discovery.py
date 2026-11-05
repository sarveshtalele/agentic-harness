import os
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class SkillMetadata(BaseModel):
    name: str
    displayName: str
    description: str
    category: str
    source: str
    path: str
    command: str
    argumentHint: Optional[str] = None
    author: Optional[str] = "Unknown"
    version: Optional[str] = "1.0.0"
    content: Optional[str] = ""
    assignedAgent: Optional[str] = "principal-test-architect"

class LocalSkillDiscovery:
    """
    Dynamically discovers and loads all actual skills installed on the local machine.
    Scans:
      - /Users/sarveshtalele/Downloads/agentic-qe/skills
      - ~/.claude/skills
      - ~/.agents/skills
      - ~/.gemini/antigravity/builtin/skills and ~/.gemini/antigravity/skills
      - Workspace root ./skills
    """
    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()
        self._cache: Dict[str, SkillMetadata] = {}
        self.scan_local_skills()

    def get_search_paths(self) -> List[tuple[str, str, str]]:
        """
        Returns list of tuples: (directory_path, source_label, category_label)
        """
        home = os.path.expanduser("~")
        paths = [
            # 1. agentic-qe repository skills
            (
                os.path.join(home, "Downloads", "agentic-qe", "skills"),
                "agentic-qe (Plugin)",
                "Quality Engineering"
            ),
            # 2. Local workspace skills if any
            (
                os.path.join(self.workspace_root, "skills"),
                "Workspace Skills",
                "Project Specific"
            ),
            (
                os.path.join(self.workspace_root, ".skills"),
                "Workspace Hidden Skills",
                "Project Specific"
            ),
            # 3. Claude Code local skills
            (
                os.path.join(home, ".claude", "skills"),
                "Claude Code Desktop",
                "Productivity & Code"
            ),
            # 4. Agent Skills
            (
                os.path.join(home, ".agents", "skills"),
                "Agentic Framework",
                "Autonomous Agents"
            ),
            # 5. Antigravity Builtin & Global Skills
            (
                os.path.join(home, ".gemini", "antigravity", "skills"),
                "Antigravity User Skills",
                "Modernization & Workflows"
            ),
            (
                os.path.join(home, ".gemini", "antigravity", "builtin", "skills"),
                "Antigravity Built-in",
                "System & Core"
            ),
        ]
        return [(p, s, c) for p, s, c in paths if os.path.exists(p)]

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, str], str]:
        """
        Parses YAML-style frontmatter from markdown.
        """
        frontmatter = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                yaml_block = parts[1]
                body = parts[2].strip()

                for line in yaml_block.splitlines():
                    line = line.strip()
                    if ":" in line and not line.startswith("#"):
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        frontmatter[key] = val

        return frontmatter, body

    def _map_agent_for_skill(self, skill_name: str, desc: str) -> str:
        s_lower = f"{skill_name} {desc}".lower()
        if "security" in s_lower or "audit" in s_lower:
            return "security-compliance-specialist"
        if "discover" in s_lower or "analyz" in s_lower or "repo" in s_lower:
            return "repo-intelligence-analyst"
        if "plan" in s_lower or "strategy" in s_lower:
            return "principal-test-architect"
        if "design" in s_lower or "case" in s_lower or "requirement" in s_lower or "stories" in s_lower:
            return "test-design-architect"
        if "generate" in s_lower or "code" in s_lower or "data" in s_lower:
            return "test-automation-engineer"
        if "run" in s_lower or "execute" in s_lower:
            return "qa-execution-engineer"
        if "heal" in s_lower or "doctor" in s_lower or "diagnos" in s_lower:
            return "defect-diagnostician"
        if "trace" in s_lower or "coverage" in s_lower:
            return "coverage-auditor"
        if "sign" in s_lower or "review" in s_lower or "confidence" in s_lower:
            return "confidence-reviewer"
        return "principal-test-architect"

    def scan_local_skills(self) -> Dict[str, SkillMetadata]:
        skills_found: Dict[str, SkillMetadata] = {}

        for dir_path, source_label, category_label in self.get_search_paths():
            try:
                for entry in os.scandir(dir_path):
                    if entry.is_dir():
                        skill_md = os.path.join(entry.path, "SKILL.md")
                        if os.path.isfile(skill_md):
                            try:
                                with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
                                    raw = f.read()

                                fm, body = self._parse_frontmatter(raw)
                                skill_name = fm.get("name") or entry.name
                                description = fm.get("description") or ""

                                # If no description in frontmatter, extract first heading/paragraph
                                if not description and body:
                                    lines = [l.strip() for l in body.splitlines() if l.strip() and not l.startswith("#")]
                                    description = lines[0] if lines else f"Skill {skill_name}"

                                # Clean description
                                description = re.sub(r"\s+", " ", description).strip()
                                if len(description) > 180:
                                    description = description[:177] + "..."

                                display_name = skill_name.replace("-", " ").title()

                                assigned_agent = self._map_agent_for_skill(skill_name, description)

                                meta = SkillMetadata(
                                    name=skill_name,
                                    displayName=display_name,
                                    description=description,
                                    category=category_label,
                                    source=source_label,
                                    path=skill_md,
                                    command=f"/skill {skill_name}",
                                    argumentHint=fm.get("argument-hint"),
                                    author=fm.get("author", "Sarvesh Talele"),
                                    version=fm.get("version", "1.0.0"),
                                    content=body,
                                    assignedAgent=assigned_agent
                                )
                                skills_found[skill_name] = meta
                            except Exception as e:
                                continue
            except Exception:
                continue

        self._cache = skills_found
        return self._cache

    def list_skills(self) -> List[Dict[str, Any]]:
        if not self._cache:
            self.scan_local_skills()
        return [s.model_dump() for s in sorted(self._cache.values(), key=lambda x: (x.category, x.name))]

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        if not self._cache:
            self.scan_local_skills()
        norm = name.lower().strip().replace("/skill", "").replace("/", "").strip()
        return self._cache.get(norm)
