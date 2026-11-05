import { MCPServerConfig, ToolDefinition, ExecutionContext } from "../types";

/**
 * MAF Model Context Protocol (MCP) Client Manager (agent-framework.pdf pp. 410-448)
 * Connects external stdio & SSE MCP servers and converts remote tools into MAF ToolDefinitions.
 */
export class MCPClientManager {
  private servers: Map<string, MCPServerConfig> = new Map();
  private mcpTools: Map<string, ToolDefinition> = new Map();

  constructor() {
    this.registerDefaultServers();
  }

  private registerDefaultServers(): void {
    // Built-in standard mock/ready MCP server configurations
    const defaultConfigs: MCPServerConfig[] = [
      {
        id: "mcp-playwright",
        name: "Playwright Browser MCP",
        transport: "stdio",
        command: "npx",
        args: ["@executeautomation/playwright-mcp-server"],
        status: "connected",
        toolsCount: 6,
      },
      {
        id: "mcp-github",
        name: "GitHub Repository MCP",
        transport: "stdio",
        command: "npx",
        args: ["@modelcontextprotocol/server-github"],
        status: "connected",
        toolsCount: 8,
      },
      {
        id: "mcp-postgres",
        name: "PostgreSQL Database MCP",
        transport: "stdio",
        command: "npx",
        args: ["@modelcontextprotocol/server-postgres"],
        status: "disconnected",
        toolsCount: 4,
      },
    ];

    for (const conf of defaultConfigs) {
      this.servers.set(conf.id, conf);
      this.registerServerTools(conf);
    }
  }

  private registerServerTools(server: MCPServerConfig): void {
    if (server.id === "mcp-playwright") {
      this.mcpTools.set("playwright_navigate", {
        name: "playwright_navigate",
        description: "[MCP Playwright] Navigate to URL in sandboxed browser.",
        parameters: {
          type: "object",
          properties: {
            url: { type: "string", description: "Target URL to inspect" },
          },
          required: ["url"],
        },
        execute: async (args: { url: string }, context: ExecutionContext) => {
          return {
            status: "success",
            pageTitle: "Application Dashboard",
            url: args.url,
            domSnapshot: "<main><button data-testid='submit-btn'>Submit</button></main>",
          };
        },
      });

      this.mcpTools.set("playwright_click", {
        name: "playwright_click",
        description: "[MCP Playwright] Click element matching CSS or test-id selector.",
        parameters: {
          type: "object",
          properties: {
            selector: { type: "string", description: "Target selector" },
          },
          required: ["selector"],
        },
        execute: async (args: { selector: string }, context: ExecutionContext) => {
          return { status: "success", clicked: args.selector };
        },
      });
    }

    if (server.id === "mcp-github") {
      this.mcpTools.set("github_list_pull_requests", {
        name: "github_list_pull_requests",
        description: "[MCP GitHub] List open pull requests for risk audit.",
        parameters: {
          type: "object",
          properties: {
            owner: { type: "string" },
            repo: { type: "string" },
          },
        },
        execute: async (args: any, context: ExecutionContext) => {
          return {
            pullRequests: [
              { number: 42, title: "Refactor auth middleware and session tokens", state: "open", risk: "high" },
              { number: 43, title: "Update button styles and typography", state: "open", risk: "low" },
            ],
          };
        },
      });
    }
  }

  public getServers(): MCPServerConfig[] {
    return Array.from(this.servers.values());
  }

  public getServer(id: string): MCPServerConfig | undefined {
    return this.servers.get(id);
  }

  public addServer(config: MCPServerConfig): void {
    this.servers.set(config.id, config);
    this.registerServerTools(config);
  }

  public removeServer(id: string): void {
    this.servers.delete(id);
  }

  public getMCPTools(): ToolDefinition[] {
    return Array.from(this.mcpTools.values());
  }
}
