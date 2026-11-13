"use client";

import { PageTitle } from "../../components/ui";
import { AppShell } from "../../components/AppShell";
import { useAuth } from "../../components/AuthGate";
import { ConnectionsCard } from "../../features/settings/ConnectionsCard";
import { FeatureAccess } from "../../features/settings/FeatureAccess";
import { GateRoles } from "../../features/settings/GateRoles";
import { HealthCard } from "../../features/settings/HealthCard";
import { LogCard } from "../../features/settings/LogCard";
import { ModelList } from "../../features/settings/ModelList";
import { PluginsCard } from "../../features/plugins/PluginsCard";
import { ModelProviderCard } from "../../features/settings/ModelProviderCard";

export default function SettingsPage() {
  const { user } = useAuth();
  return (
    <AppShell>
      <PageTitle title="Settings" />
      <div className="space-y-4">
        <HealthCard />
        <ModelProviderCard />
        {user?.role === "admin" && <ModelList />}
        {user?.role === "admin" && <FeatureAccess />}
        {user?.role === "admin" && <GateRoles />}
        {user?.role === "admin" && <LogCard />}
        <PluginsCard />
        <ConnectionsCard />
      </div>
    </AppShell>
  );
}
