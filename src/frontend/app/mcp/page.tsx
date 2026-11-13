"use client";

import { AppShell } from "../../components/AppShell";
import { PageTitle } from "../../components/ui";
import { McpRegistry } from "../../features/mcp/McpRegistry";

export default function McpPage() {
  return (
    <AppShell>
      <PageTitle title="MCP servers" />
      <McpRegistry />
    </AppShell>
  );
}
