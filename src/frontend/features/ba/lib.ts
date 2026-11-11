export function getDomainPresets(projectName: string, repoUrl: string) {
  const isMcp = projectName.toLowerCase().includes("mcp") || repoUrl.toLowerCase().includes("mcp");
  if (isMcp) {
    return [
      {
        name: "MCP Gateway & Registry",
        title: "Model Context Protocol (MCP) Server Gateway & Discovered Tools Specification",
        brief: "Author an enterprise-grade Business Requirements Document (BRD) for a Model Context Protocol (MCP) Gateway and Server Registry. Must specify dynamic STDIO and SSE transports, automated tool authorization flags, AST schema validation for tool input/output, rate limiting, and cryptographic execution logs.",
      },
      {
        name: "Remote SSE Client",
        title: "Enterprise MCP Remote SSE Streaming & Proxy Client Specification",
        brief: "Author a comprehensive Business Requirements Document (BRD) for an enterprise Remote MCP SSE Proxy and Client. Includes HTTP/HTTPS token authentication, streaming event-source keep-alives, automatic reconnect with exponential backoff, and sandboxed isolated tool execution.",
      },
      {
        name: "Tool Sandbox Isolation",
        title: "Zero-Trust Subprocess Sandbox & MCP Security Policy Specification",
        brief: "Author a complete Business Requirements Document (BRD) for an isolated subprocess execution sandbox running local NPX and Node MCP servers. Enforces strict env isolation, forbidden shell pattern detection, and token budget ceilings.",
      },
      {
        name: "Traceability & Coverage",
        title: "MCP End-to-End Traceability Matrix & Test Strategy Specification",
        brief: "Author a formal Business Requirements Document (BRD) for full test traceability and contract verification covering Playwright browser automation tools, SQLite query engines, and GitHub Copilot endpoints.",
      },
    ];
  }
  return [
    {
      name: "Core Service & API",
      title: `${projectName} Core Service & REST/GraphQL API Specification`,
      brief: `Author an enterprise-grade Business Requirements Document (BRD) for ${projectName} defining core domain workflows, RESTful and streaming endpoints, payload validation schemas, idempotent transaction processing, and observability hooks.`,
    },
    {
      name: "Auth & Access Control",
      title: `${projectName} Role-Based Access Control (RBAC) & Security Policy`,
      brief: `Author a comprehensive Business Requirements Document (BRD) for ${projectName} defining user authentication, cryptographic session cookies, permission matrices (Developer, Reviewer, Admin), and audit ledger trails.`,
    },
    {
      name: "Data Model & Ledger",
      title: `${projectName} Immutable Audit Ledger & Persistence Architecture`,
      brief: `Author a complete Business Requirements Document (BRD) for ${projectName} specifying database schema, migration pipelines, append-only event logging, deterministic test assertions, and disaster recovery.`,
    },
    {
      name: "E2E Quality & Oracles",
      title: `${projectName} Deterministic Testing Lifecycle & Quality Gate Criteria`,
      brief: `Author a complete Business Requirements Document (BRD) for ${projectName} establishing quality gate criteria (G0 to G5), Gherkin executable specifications, JUnit reporting, and automated healing workflows.`,
    },
  ];
}

export const getFileBadgeTone = (name: string) => {
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf")) return "rose";
  if (lower.endsWith(".docx") || lower.endsWith(".doc")) return "indigo";
  if (lower.endsWith(".xlsx") || lower.endsWith(".csv")) return "emerald";
  return "slate";
};
