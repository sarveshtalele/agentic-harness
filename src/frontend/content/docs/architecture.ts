import type { DocGroup } from "./types";

export const architecture: DocGroup = {
    title: "Architecture & Standards",
    pages: [
      {
        slug: "system-architecture-design",
        title: "System Architecture & Design",
        summary: "Production architecture: 6-gate state machine, micro-agent roster, AST parsing, and zero-trust sandbox execution.",
        body: `## Canonical Architecture & System Design

The **Agentic Quality Engineering (QE) Platform** is an enterprise-grade autonomous testing and verification ecosystem built on **Microsoft Agent Framework (MAF)**, **Next.js 16 App Router**, and **FastAPI**. It transforms raw repository code, specifications, or business requirements into comprehensive, level-allocated, deterministic, and self-healing test suites with complete cryptographic traceability.

### Core Architectural Tenets

1. **Zero Hallucinated Evidence (Anti-Hallucination Gateways):** No requirement, bug finding, or test case is accepted into the system without disk-verified evidence. Every code quote is checked against disk line-by-line using abstract syntax trees (AST) and normalized text search (\`static_analysis.verify_quote\`). Quotes originating from comments are rejected; executable code strictly takes precedence over comments.
2. **Dual-Layer Sandbox Isolation & Credential Scrubbing:** Untrusted repository code and test execution run in isolated Git worktrees (\`atlas/qe-*\` branches) under a scrubbed environment (\`clean_env()\`). Ambient platform secrets, API tokens, passwords, and cloud credentials matching \`(?i)(key|secret|token|password|auth|cred|atlas|openai|anthropic)\` are purged prior to any subprocess execution.
3. **Deterministic Token Predictability over Open-Ended Tool Loops:** Workflow agents receive structured line-numbered context packs (\`code_pack\`) directly in their conversation turn and possess zero tools. Structured code packing achieves superior test suite compilation within ~86,000 tokens compared to drifting tool loops (170k-955k tokens).
4. **Durable Human-in-the-Loop Quality Gates (G0–G7):** Workflows progress through formal quality gates requiring HMAC-signed decisions by authenticated, role-authorized human reviewers. Stages persist intermediate states to SQLite WAL and file-backed checkpoints (\`FileCheckpointStorage\`), surviving process interruptions and server restarts.
5. **Assertion-Preserving Self-Healing:** Autonomous self-healing is strictly bounded to repairing test selectors and fixture definitions. Code guardrails (\`guarded_apply\`) reject any automated repair that modifies, removes, or weakens test assertions, introduces test skips, or touches application production code.
6. **Single Source of Truth:** One single canonical document governs each architectural concern. Redundant, divergent, or dead specification files are eliminated.

See the complete production specification in \`docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md\`.`,
      },
      {
        slug: "azure-enterprise-deployment-guide",
        title: "Azure Enterprise Cloud Deployment",
        summary: "Production Azure architecture: App Service, PostgreSQL, Blob Storage, Key Vault, Container Apps Sandboxes, and Kudu zero-downtime deployment.",
        body: `## Azure Enterprise Deployment Guide

This canonical specification provides an exhaustive, production-grade deployment roadmap for hosting the Agentic QE Platform on **Microsoft Azure**.

### Architectural Deployment Topology

- **Web Tier (Frontend):** Azure App Service (Linux, Node.js 20 LTS) serving Next.js 16 App Router.
- **API & Orchestration Tier (Backend):** Azure App Service (Linux, Python 3.12 LTS) serving FastAPI and Microsoft Agent Framework (MAF).
- **Relational Data Tier:** Azure Database for PostgreSQL Flexible Server (Zone-Redundant HA, Private Endpoint).
- **Blob & Artifact Tier:** Azure Blob Storage with immutability policies, lifecycle archiving, and customer-managed keys (CMK).
- **Secrets & Configuration:** Azure Key Vault with Managed Identities and Azure App Configuration.
- **Untrusted Code Sandbox:** Azure Container Apps (ACA) Dynamic Sessions providing ephemeral gVisor-isolated container sandboxes for repository cloning, AST analysis, and test runners.
- **Security & Edge (target design, not deployed):** Azure Front Door with WAF rules in front of the backend.

### Zero-Downtime Deployment via Kudu

Deployments utilize Azure App Service Deployment Slots (Blue/Green) with Kudu zip deployment:
\`\`\`bash
az webapp deployment source config-zip --resource-group rg-agentic-qe-prod --name app-agentic-qe-backend-prod --src backend.zip
\`\`\`

See the complete deployment guide in \`docs/AZURE_ENTERPRISE_DEPLOYMENT_GUIDE.md\`.`,
      },
      {
        slug: "security-governance-audit",
        title: "Security, Governance & Guardrails",
        summary: "Prompt-injection framing, secret redaction, deny-by-default routes, and the role matrix.",
        body: `## Security Governance, Guardrails & Audit

This canonical document consolidates the end-to-end security architecture, threat model, compliance posture, and remediation evidence across the Agentic QE Platform.

### Multi-Layer Security Architecture

1. **Deterministic Input Sanitation & Injection Scrubbing:**
   - Pre-execution regex and semantic scanning for prompt injection patterns.
   - Demarcation delimiters (\`<<<EXTERNAL_UNTRUSTED_CONTENT>>>\`) isolating repository files from agent instructions.
2. **Bidirectional Secret Scrubbing & Redaction:**
   - Real-time scrubbing of API keys, bearer tokens, private keys, database connection strings, and cloud credentials in inputs, outputs, and log streams.
3. **Dual-Layer Sandbox Isolation:**
   - Ephemeral Git worktrees scrubbed of host environment variables.
   - Subprocess execution timeout limits and fail-closed termination.
4. **Zero-Trust Human-in-the-Loop Quality Gates:**
   - Cryptographic HMAC-SHA256 signature auditing on all approval gate decisions.
   - Role-Based Access Control (RBAC): Admin, QA Architect, Developer, Business Analyst, Auditor.
5. **Skill scanning (planned, P6):**
   - NVIDIA SkillSpector will scan skill definitions and scripts. Until then no skill security score is shown.

See the complete audit and remediation details in \`docs/SECURITY_GOVERNANCE_AND_AUDIT.md\`.`,
      },
      {
        slug: "agent-skills-maf-specification",
        title: "Agent Skills & MAF Specification",
        summary: "Progressive disclosure standard, SKILL.md schema, sandboxed execution, and offline deterministic evaluation criteria.",
        body: `## Agent Skills & MAF Specification

This canonical document establishes the architectural standard and runtime specification for **Agent Skills** and **Microsoft Agent Framework (MAF)** integration within the platform.

### Core Skill Tenets & Standards

1. **Progressive Disclosure:** Skills advertise lightweight metadata (name, description, tags) during initial agent discovery. Full instructions and resource files are loaded on-demand, keeping agent system prompts compact and cost-efficient.
2. **Predictable Schema Compliance:** Every skill adheres strictly to the Agent Skills standard:
   - Root directory with lowercase alphanumeric name and hyphens.
   - \`SKILL.md\` file with YAML frontmatter (\`name\`, \`description\`) and markdown instructions.
   - Optional \`scripts/\` directory containing executable Python or shell runners.
   - Optional \`resources/\` directory containing deterministic reference data, templates, or schemas.
3. **Sandboxed Subprocess Execution:** Skill scripts execute strictly inside isolated environments with scrubbed credentials and execution timeouts.
4. **MAF Native Integration:** Seamlessly bridges to MAF \`ChatAgent\`, \`WorkflowEngine\`, and \`TodoProvider\`.

See the complete specification and guidelines in \`docs/AGENT_SKILLS_AND_MAF_SPECIFICATION.md\`.`,
      },
    ],
};
