"""
NVIDIA Skill Specter AST & Security Scanner
Performs static AST analysis, prompt injection demarcation verification,
path traversal checks, and secret leakage audits on agent skills.

Scoring Standard:
- Security Risk Score (0-100):
    0-15:   CLEAN / LOW RISK (Production Ready)
    16-39:  MEDIUM RISK (Requires Audit)
    40-69:  HIGH RISK (Requires Approval)
    70-100: CRITICAL RISK (Blocked / NOT Ready for Use)
- Governance Health Score (0-100%): Quality & standard alignment (e.g. 98% = A+ Grade).
"""

from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class SpecterFinding:
    def __init__(
        self,
        check_id: str,
        name: str,
        severity: str,  # "critical", "high", "medium", "low", "info"
        description: str,
        file: str,
        line: Optional[int] = None,
        recommendation: str = ""
    ):
        self.check_id = check_id
        self.name = name
        self.severity = severity
        self.description = description
        self.file = file
        self.line = line
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "severity": self.severity,
            "description": self.description,
            "file": self.file,
            "line": self.line,
            "recommendation": self.recommendation,
        }


class PythonASTSecurityVisitor(ast.NodeVisitor):
    """Inspects Python code AST for dangerous subprocess calls, eval/exec, and path traversal."""

    def __init__(self, filename: str):
        self.filename = filename
        self.findings: List[SpecterFinding] = []

    def visit_Call(self, node: ast.Call):
        # 1. Check for eval() and exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "__import__", "compile"):
                self.findings.append(
                    SpecterFinding(
                        check_id="SPECTER-RCE-01",
                        name="Arbitrary Code Execution Primitive",
                        severity="critical",
                        description=f"Use of dangerous built-in '{node.func.id}()' enables arbitrary code execution.",
                        file=self.filename,
                        line=node.lineno,
                        recommendation="Remove dynamic evaluation. Use structured parsers (json, yaml) instead."
                    )
                )

        # 2. Check for os.system or os.popen
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                if node.func.attr in ("system", "popen", "spawnl", "spawnlp"):
                    self.findings.append(
                        SpecterFinding(
                            check_id="SPECTER-SHELL-01",
                            name="Unrestricted Shell Command Execution",
                            severity="critical",
                            description=f"Use of 'os.{node.func.attr}()' bypasses subprocess sandboxing.",
                            file=self.filename,
                            line=node.lineno,
                            recommendation="Replace with subprocess.run() without shell=True and with explicit argument lists."
                        )
                    )

            # 3. Check for subprocess calls with shell=True
            if isinstance(node.func.value, ast.Name) and node.func.value.id in ("subprocess", "asyncio"):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        self.findings.append(
                            SpecterFinding(
                                check_id="SPECTER-SHELL-02",
                                name="Subprocess Invoked with shell=True",
                                severity="critical",
                                description="Executing commands through a shell enables command injection.",
                                file=self.filename,
                                line=node.lineno,
                                recommendation="Pass arguments as a list of strings and set shell=False."
                            )
                        )

        self.generic_visit(node)


def scan_skill_security(skill_dir_path: str | Path) -> Dict[str, Any]:
    """
    Performs comprehensive NVIDIA Skill Specter security audit on a skill directory.
    Evaluates:
    1. Python script AST safety
    2. Prompt injection demarcation in SKILL.md
    3. Secret and credential leakage
    4. Sandbox path confinement
    """
    skill_dir = Path(skill_dir_path)
    if not skill_dir.is_dir():
        return {
            "status": "ERROR",
            "error": f"Skill path does not exist or is not a directory: {skill_dir}",
            "riskScore": 100,
            "readinessStatus": "BLOCKED",
            "grade": "F",
            "findings": []
        }

    findings: List[SpecterFinding] = []
    checks_passed: List[str] = []

    # 1. Audit SKILL.md for Frontmatter & Prompt Injection Demarcation
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        findings.append(
            SpecterFinding(
                check_id="SPECTER-SPEC-01",
                name="Missing SKILL.md Contract",
                severity="critical",
                description="Agent skill root lacks required SKILL.md specification file.",
                file="SKILL.md",
                recommendation="Create SKILL.md with standard YAML frontmatter conforming to MAF 2.0."
            )
        )
    else:
        content = skill_md.read_text(encoding="utf-8", errors="ignore")
        if not content.startswith("---"):
            findings.append(
                SpecterFinding(
                    check_id="SPECTER-SPEC-02",
                    name="Missing Frontmatter Demarcation",
                    severity="high",
                    description="SKILL.md does not begin with YAML frontmatter delimiters ('---').",
                    file="SKILL.md",
                    recommendation="Add frontmatter with name, description, and metadata fields."
                )
            )
        else:
            checks_passed.append("YAML Frontmatter Boundary Demarcated")

        # Scan for Prompt Injection / Delimiter Bypass Patterns
        injection_patterns = [
            (r"(?i)ignore\s+(all\s+)?previous\s+instructions", "Prompt Injection Instruction Override"),
            (r"(?i)system\s*override", "System Override Directive"),
            (r"(?i)disregard\s+safety\s+guidelines", "Safety Bypass Directive"),
            (r"(?i)<\s*script[^>]*>", "HTML Script Tag Injection"),
        ]
        for pattern, label in injection_patterns:
            if re.search(pattern, content):
                findings.append(
                    SpecterFinding(
                        check_id="SPECTER-INJ-01",
                        name=f"Prompt Injection Pattern: {label}",
                        severity="critical",
                        description=f"Skill documentation contains high-risk prompt injection trigger: '{label}'.",
                        file="SKILL.md",
                        recommendation="Sanitize instructions. Never allow instructions that command the model to ignore safety rules."
                    )
                )
        if not any(f.check_id.startswith("SPECTER-INJ") for f in findings):
            checks_passed.append("Prompt Injection & Jailbreak Demarcation Verified")

    # 2. Audit Python Scripts with AST Analysis
    scripts_dir = skill_dir / "scripts"
    py_files = list(scripts_dir.glob("*.py")) if scripts_dir.is_dir() else []
    for py_file in py_files:
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=py_file.name)
            visitor = PythonASTSecurityVisitor(filename=py_file.name)
            visitor.visit(tree)
            findings.extend(visitor.findings)
        except SyntaxError as e:
            findings.append(
                SpecterFinding(
                    check_id="SPECTER-AST-01",
                    name="Python Syntax Error in Runner",
                    severity="high",
                    description=f"Script failed AST parsing: {e}",
                    file=py_file.name,
                    line=e.lineno,
                    recommendation="Fix Python syntax to allow automated security AST verification."
                )
            )

    if not any(f.check_id.startswith("SPECTER-RCE") or f.check_id.startswith("SPECTER-SHELL") for f in findings):
        checks_passed.append("Subprocess Sandboxing & Subprocess AST Confinement Verified")

    # 3. Secret & Credential Leakage Scan
    secret_patterns = [
        (r"sk-[a-zA-Z0-9]{32,}", "OpenAI API Key"),
        (r"ghp_[a-zA-Z0-9]{36,}", "GitHub Personal Access Token"),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
        (r"-----BEGIN (?:RSA )?PRIVATE KEY-----", "Private Cryptographic Key"),
    ]
    all_files = list(skill_dir.rglob("*.py")) + list(skill_dir.rglob("*.json")) + list(skill_dir.rglob("*.md"))
    for fpath in all_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            rel_path = str(fpath.relative_to(skill_dir))
            for pattern, sec_name in secret_patterns:
                if re.search(pattern, text):
                    findings.append(
                        SpecterFinding(
                            check_id="SPECTER-SEC-01",
                            name=f"Exposed Secret: {sec_name}",
                            severity="critical",
                            description=f"File contains hardcoded credential matching pattern '{sec_name}'.",
                            file=rel_path,
                            recommendation="Remove hardcoded secrets immediately. Use environment variables or secret managers."
                        )
                    )
        except Exception:
            continue

    if not any(f.check_id.startswith("SPECTER-SEC") for f in findings):
        checks_passed.append("Zero Secret & Credential Leakage Verified")

    # 4. Path Traversal & Filesystem Confinement
    for py_file in py_files:
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        if "../" in text or "..\\" in text:
            findings.append(
                SpecterFinding(
                    check_id="SPECTER-PATH-01",
                    name="Potential Path Traversal Pattern",
                    severity="medium",
                    description="Script references relative parent directory traversal ('../').",
                    file=py_file.name,
                    recommendation="Resolve all file paths strictly relative to the sandbox working directory."
                )
            )

    if not any(f.check_id.startswith("SPECTER-PATH") for f in findings):
        checks_passed.append("Path Traversal & Sandbox Directory Escape Defense Verified")

    # 5. Compute Risk Score & Health Grade
    # Standard: High risk score means CRITICAL and NOT ready for use!
    # Critical finding = +35 points, High = +20, Medium = +10, Low = +5
    risk_points = 0
    for f in findings:
        if f.severity == "critical":
            risk_points += 35
        elif f.severity == "high":
            risk_points += 20
        elif f.severity == "medium":
            risk_points += 10
        elif f.severity == "low":
            risk_points += 5

    risk_score = min(100, risk_points)

    # Determine Readiness Status
    if risk_score >= 40:
        readiness_status = "CRITICAL / NOT READY FOR USE"
        grade = "FAIL"
    elif risk_score >= 15:
        readiness_status = "AUDIT REQUIRED"
        grade = "B"
    else:
        readiness_status = "VERIFIED / PRODUCTION READY"
        grade = "A+"

    health_score = max(0, 100 - risk_score)

    return {
        "skill": skill_dir.name,
        "path": str(skill_dir),
        "riskScore": risk_score,
        "healthScore": health_score,
        "readinessStatus": readiness_status,
        "grade": grade,
        "isReady": risk_score < 40,
        "findings": [f.to_dict() for f in findings],
        "findingsCount": len(findings),
        "criticalCount": sum(1 for f in findings if f.severity == "critical"),
        "highCount": sum(1 for f in findings if f.severity == "high"),
        "checksPassed": checks_passed,
        "summary": (
            f"NVIDIA Skill Specter Security Audit: Risk Score {risk_score}/100 "
            f"({readiness_status}). {len(findings)} findings, {len(checks_passed)} safety checks verified."
        )
    }
