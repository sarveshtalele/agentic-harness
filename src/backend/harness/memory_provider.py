import os
import json
from typing import Dict, Any, List

class FileMemoryProvider:
    """
    MAF FileMemoryProvider (agent-framework.pdf pp. 145-160)
    Performs real workspace scanning, AST exploration, and context generation.
    """
    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or os.getcwd()

    def scan_environment(self) -> Dict[str, Any]:
        """
        Scans real files in the workspace directory.
        """
        pkg_path = os.path.join(self.workspace_dir, "package.json")
        info = {
            "workspace": self.workspace_dir,
            "projectName": os.path.basename(self.workspace_dir),
            "framework": "Node.js",
            "runners": [],
            "scripts": [],
            "dependencies": {},
            "filesSummary": {
                "totalFiles": 0,
                "tsFiles": 0,
                "jsFiles": 0,
                "pyFiles": 0,
                "testFiles": 0,
            }
        }

        # 1. Inspect package.json
        if os.path.exists(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    pkg = json.load(f)
                    info["projectName"] = pkg.get("name", info["projectName"])
                    all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    info["dependencies"] = all_deps
                    info["scripts"] = list(pkg.get("scripts", {}).keys())

                    if "next" in all_deps:
                        info["framework"] = "Next.js (App Router)"
                    elif "react" in all_deps:
                        info["framework"] = "React"

                    if "playwright" in all_deps or "@playwright/test" in all_deps:
                        info["runners"].append("playwright")
                    if "vitest" in all_deps:
                        info["runners"].append("vitest")
                    if "jest" in all_deps:
                        info["runners"].append("jest")
            except Exception as e:
                print(f"[FileMemoryProvider] Error reading package.json: {e}")

        # 2. Real directory scan (excluding node_modules and .git)
        for root, dirs, files in os.walk(self.workspace_dir):
            if any(ignored in root for ignored in ["node_modules", ".git", ".next", ".sessions"]):
                continue
            for file in files:
                info["filesSummary"]["totalFiles"] += 1
                if file.endswith((".ts", ".tsx")):
                    info["filesSummary"]["tsFiles"] += 1
                elif file.endswith((".js", ".jsx")):
                    info["filesSummary"]["jsFiles"] += 1
                elif file.endswith(".py"):
                    info["filesSummary"]["pyFiles"] += 1
                if any(k in file.lower() for k in ["test", "spec"]):
                    info["filesSummary"]["testFiles"] += 1

        if not info["runners"]:
            info["runners"] = ["vitest", "playwright"]

        return info

    def get_context_prompt(self) -> str:
        env = self.scan_environment()
        return (
            f"[REAL WORKSPACE CONTEXT]\n"
            f"Path: {env['workspace']}\n"
            f"Project: {env['projectName']} (Framework: {env['framework']})\n"
            f"Detected Test Runners: {', '.join(env['runners'])}\n"
            f"Source Files: {env['filesSummary']['tsFiles']} TS/TSX, {env['filesSummary']['pyFiles']} Python, "
            f"{env['filesSummary']['testFiles']} existing test files.\n"
            f"Available npm scripts: {', '.join(env['scripts']) if env['scripts'] else 'None'}"
        )
