"use client";

import { AppShell } from "../../components/AppShell";
import { PageTitle } from "../../components/ui";
import { CapabilitiesPage } from "../../features/capabilities/CapabilitiesPage";

export default function Capabilities() {
  return (
    <AppShell>
      <PageTitle title="Capability registry" subtitle="Every tool, agent, skill, command, workflow, plugin and MCP tool, read from the code and manifests by a sync, with how they connect. You see what you may use." />
      <CapabilitiesPage />
    </AppShell>
  );
}
