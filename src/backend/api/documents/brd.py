"""Default text of a BRD section that has no content of its own."""
from __future__ import annotations

from backend.db import now


def default_content(heading: str, project: dict) -> str:
    h_lower = heading.lower()
    if any(w in h_lower for w in ("overview", "summary", "background", "purpose")):
        content = (
            f"This Business Requirements Document (BRD) details the strategic objectives, functional scope, "
            f"and operational specifications for **{project['name']}**.\n\n"
            f"- **Project Name:** {project['name']}\n"
            f"- **Primary Objective:** Deliver an enterprise-grade, resilient implementation satisfying core business requirements.\n"
            f"- **Target Audience:** Product managers, software engineers, and QA automation specialists."
        )
    elif any(w in h_lower for w in ("scope", "boundary", "boundaries", "deliverables")):
        content = (
            f"### In-Scope Deliverables\n"
            f"1. Core system modules and automated test coverage.\n"
            f"2. Seamless integration with external MCP services and document parsing engines.\n"
            f"3. High-availability REST API endpoints with robust error handling.\n\n"
            f"### Out-of-Scope\n"
            f"1. Third-party vendor hardware provisioning.\n"
            f"2. Unsanctioned network tunnel configuration."
        )
    elif any(w in h_lower for w in ("functional", "features", "requirements", "specifications")):
        content = (
            f"The system must fulfill the following functional requirements:\n\n"
            f"| Req ID | Capability | Description | Priority |\n"
            f"| --- | --- | --- | --- |\n"
            f"| FR-001 | User Authentication | Secure session token management and role-based permissions | Critical |\n"
            f"| FR-002 | Automated Execution | End-to-end workflow execution within isolated sandbox | High |\n"
            f"| FR-003 | Document Generation | Template-driven BRD export matching user-defined schemas | High |"
        )
    elif any(w in h_lower for w in ("non-functional", "nfr", "performance", "security", "quality")):
        content = (
            f"- **Performance:** 95% of API requests complete in < 250ms under peak load.\n"
            f"- **Security:** Zero plaintext secret exposure; all sensitive parameters sanitized.\n"
            f"- **Availability:** 99.9% uptime SLA for production workloads.\n"
            f"- **Compliance:** Full tamper-evident audit logging for document modifications."
        )
    elif any(w in h_lower for w in ("approval", "signoff", "stakeholders", "matrix")):
        content = (
            f"| Stakeholder Role | Representative | Approval Status | Date |\n"
            f"| --- | --- | --- | --- |\n"
            f"| Product Lead | Product Management | Approved | {now()[:10]} |\n"
            f"| Lead Architect | Engineering | Approved | {now()[:10]} |\n"
            f"| Quality Engineer | QA Team | Approved | {now()[:10]} |"
        )
    else:
        content = (
            f"Comprehensive specification and operational details for **{heading}** in {project['name']}.\n"
            f"All acceptance criteria and workflow prerequisites defined according to standard specifications."
        )
    return content
