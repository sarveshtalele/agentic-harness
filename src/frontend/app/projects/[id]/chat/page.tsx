"use client";

import { Chat } from "../../../../features/chat/Chat";
import { useProject } from "../../../../components/ProjectShell";

export default function ChatPage() {
  const { project } = useProject();
  return <Chat projectId={project.id} />;
}
