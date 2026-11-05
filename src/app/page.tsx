"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { LeftSidebar, SessionItem } from "@/components/left-sidebar/LeftSidebar";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { ContextInspector } from "@/components/inspector/ContextInspector";
import { MCPSettingsModal } from "@/components/modals/MCPSettingsModal";
import { ModelConfigModal } from "@/components/modals/ModelConfigModal";
import { SessionState, ChatMessage, ToolCall } from "@/lib/maf/types";
import { getAgent } from "@/lib/qe/agents";
import { AGUIProtocolHandler } from "@/lib/maf/protocol/agui";

export default function Home() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [agentsList, setAgentsList] = useState<any[]>([]);
  const [pluginsList, setPluginsList] = useState<any[]>([]);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [skillsList, setSkillsList] = useState<any[]>([]);
  const [currentModel, setCurrentModel] = useState("gpt-4o");
  const [isModelConfigured, setIsModelConfigured] = useState<boolean>(false);

  // Layout states
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [mcpModalOpen, setMcpModalOpen] = useState(false);
  const [modelConfigModalOpen, setModelConfigModalOpen] = useState(false);

  // Streaming & Stop states
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingThought, setStreamingThought] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch LLM configuration
  const loadConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const data = await res.json();
        if (data.model) setCurrentModel(data.model);
        setIsModelConfigured(Boolean(data.configured));
      }
    } catch (e) {
      console.error("Failed to load config:", e);
    }
  }, []);

  // Fetch Agents, Plugins, MCP Servers & Local Skills (58 Real Skills)
  const loadMetadata = useCallback(async () => {
    try {
      const [agRes, mcpRes, plugRes, skRes] = await Promise.all([
        fetch("/api/agents"),
        fetch("/api/mcp"),
        fetch("/api/plugins"),
        fetch("/api/skills"),
      ]);
      if (agRes.ok) {
        const agData = await agRes.json();
        if (agData.agents) setAgentsList(agData.agents);
      }
      if (mcpRes.ok) {
        const mcpData = await mcpRes.json();
        if (mcpData.servers) setMcpServers(mcpData.servers);
      }
      if (plugRes.ok) {
        const plugData = await plugRes.json();
        if (plugData.plugins) setPluginsList(plugData.plugins);
      }
      if (skRes.ok) {
        const skData = await skRes.json();
        if (skData.skills) setSkillsList(skData.skills);
      }
    } catch (e) {
      console.error("Failed to load metadata:", e);
    }
  }, []);

  // Fetch all persistent sessions
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) return;
      const data = await res.json();
      if (data.sessions) {
        setSessions(data.sessions);
        if (!activeSessionId && data.sessions.length > 0) {
          selectSession(data.sessions[0].id);
        } else if (data.sessions.length === 0) {
          createNewSession("Live QE Campaign", "plan");
        }
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  }, [activeSessionId]);

  // Load a specific session
  const selectSession = async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.session) {
        setActiveSessionId(id);
        setSessionState(data.session);
      }
    } catch (err) {
      console.error(`Failed to load session ${id}:`, err);
    }
  };

  // Create new session
  const createNewSession = async (name?: string, mode: "plan" | "execute" = "plan") => {
    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name || `QE Session #${sessions.length + 1}`, mode }),
      });
      const data = await res.json();
      if (data.session) {
        setActiveSessionId(data.session.id);
        setSessionState(data.session);
        loadSessions();
      }
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  // Delete session
  const deleteSession = async (id: string) => {
    try {
      await fetch(`/api/sessions/${id}`, { method: "DELETE" });
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id) {
        if (remaining.length > 0) {
          selectSession(remaining[0].id);
        } else {
          createNewSession();
        }
      }
    } catch (err) {
      console.error(`Failed to delete session ${id}:`, err);
    }
  };

  useEffect(() => {
    loadConfig();
    loadMetadata();
    loadSessions();
  }, [loadConfig, loadMetadata, loadSessions]);

  // Mode switcher
  const handleToggleMode = async (newMode: "plan" | "execute") => {
    if (!sessionState || !activeSessionId) return;
    setSessionState((prev) => (prev ? { ...prev, mode: newMode } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode }),
      });
    } catch (e) {
      console.error("Failed to update mode:", e);
    }
  };

  // Agent selector
  const handleSelectAgent = async (agentId: string) => {
    if (!sessionState || !activeSessionId) return;
    setSessionState((prev) => (prev ? { ...prev, activeAgentId: agentId } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ activeAgentId: agentId }),
      });
    } catch (e) {
      console.error("Failed to update agent:", e);
    }
  };

  // Todo checkmark toggle
  const handleToggleTodo = async (id: string, completed: boolean) => {
    if (!sessionState || !activeSessionId) return;
    const updated = sessionState.todos.map((t) =>
      t.id === id
        ? {
            ...t,
            status: (completed ? "completed" : "pending") as "completed" | "pending",
            completedAt: completed ? Date.now() : undefined,
          }
        : t
    );
    setSessionState((prev) => (prev ? { ...prev, todos: updated } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ todos: updated }),
      });
    } catch (e) {
      console.error("Failed to update todos:", e);
    }
  };

  // Manual todo add
  const handleAddTodo = async (title: string) => {
    if (!sessionState || !activeSessionId) return;
    const newTodo = {
      id: `todo-${Date.now()}`,
      title,
      status: "pending" as const,
      createdAt: Date.now(),
      agentId: sessionState.activeAgentId,
    };
    const updated = [...sessionState.todos, newTodo];
    setSessionState((prev) => (prev ? { ...prev, todos: updated } : null));

    try {
      await fetch(`/api/sessions/${activeSessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ todos: updated }),
      });
    } catch (e) {
      console.error("Failed to add todo:", e);
    }
  };

  // Stop Execution Feature (abort controller + POST /api/stop)
  const handleStopExecution = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (activeSessionId) {
      try {
        await fetch("/api/stop", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sessionId: activeSessionId }),
        });
      } catch (e) {
        console.error("Failed to send stop signal to backend:", e);
      }
    }
    setIsStreaming(false);
  };

  // Clear messages
  const handleClearSession = async () => {
    if (!sessionState || !activeSessionId) return;
    setSessionState((prev) => (prev ? { ...prev, messages: [] } : null));
  };

  // Resolve Human-In-The-Loop Quality Gate / Tool Approval
  const handleResolveApproval = async (approvalId: string, action: string, feedback?: string) => {
    try {
      await fetch("/api/approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approvalId,
          action,
          feedback,
        }),
      });
      if (activeSessionId) {
        await selectSession(activeSessionId);
      }
    } catch (e) {
      console.error("Failed to resolve approval:", e);
    }
  };

  // Export session JSON
  const handleExportSession = () => {
    if (!sessionState) return;
    const blob = new Blob([JSON.stringify(sessionState, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sessionState.name.toLowerCase().replace(/\s+/g, "-")}-session.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // AG-UI & CopilotKit Real-time SSE Chat Stream
  const handleSendMessage = async (userMessage: string) => {
    if (!userMessage.trim() || isStreaming || !activeSessionId) return;

    // Optimistically append user message
    const optimisticUserMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: "user",
      content: userMessage,
      createdAt: Date.now(),
    };

    setSessionState((prev) =>
      prev ? { ...prev, messages: [...prev.messages, optimisticUserMsg] } : null
    );

    setIsStreaming(true);
    setStreamingThought("");
    setStreamingContent("");

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    let currentThought = "";
    let currentContent = "";
    const activeToolCalls: ToolCall[] = [];

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: activeSessionId,
          message: userMessage,
          mode: sessionState?.mode || "plan",
          agentId: sessionState?.activeAgentId,
          systemPrompt: sessionState?.systemPrompt,
        }),
        signal: abortController.signal,
      });

      if (!response.body) {
        throw new Error("No response body stream received from backend.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const event = AGUIProtocolHandler.parseEvent(line);
          if (!event) continue;

          switch (event.type) {
            case "TEXT_CHUNK":
              currentContent += event.chunk;
              setStreamingContent(currentContent);
              break;

            case "THOUGHT_CHUNK":
              currentThought += event.chunk;
              setStreamingThought(currentThought);
              break;

            case "AGENT_SWITCH":
              setSessionState((prev) =>
                prev ? { ...prev, activeAgentId: event.agentId } : null
              );
              break;

            case "STATE_DELTA":
              setSessionState((prev) => (prev ? { ...prev, ...event.delta } : null));
              break;

            case "TOOL_CALL_START":
              activeToolCalls.push({
                id: event.toolCallId,
                name: event.toolName,
                args: event.args,
                status: "running",
                gateNumber: event.gate?.gateNumber,
              });
              break;

            case "TOOL_CALL_RESULT":
              const tc = activeToolCalls.find((t) => t.id === event.toolCallId);
              if (tc) {
                tc.result = event.result;
                tc.error = event.error;
                tc.status = event.error ? "failed" : "completed";
              }
              break;

            case "TOOL_APPROVAL_REQUEST":
              const pendingTc = activeToolCalls.find((t) => t.id === event.toolCallId);
              if (pendingTc) {
                pendingTc.status = "waiting_approval";
                pendingTc.approvalRequired = true;
              } else {
                activeToolCalls.push({
                  id: event.toolCallId,
                  name: event.toolName,
                  args: event.args,
                  status: "waiting_approval",
                  approvalRequired: true,
                  gateNumber: event.gate?.gateNumber,
                });
              }
              currentContent += `\n\n🛡️ **Quality Gate Action Required:** Tool \`${event.toolName}\` requires explicit verification.\n`;
              setStreamingContent(currentContent);
              break;

            case "ERROR":
              if (event.code === "MODEL_NOT_CONFIGURED") {
                setIsModelConfigured(false);
              }
              currentContent += `\n\n> ⚠️ **Error [${event.code || "SYSTEM_ERROR"}]:** ${event.message}\n`;
              setStreamingContent(currentContent);
              break;

            case "ABORTED":
              currentContent += `\n\n⚠️ **Execution stopped by user.**`;
              setStreamingContent(currentContent);
              break;

            case "RUN_FINISHED":
              break;
          }
        }
      }

      // Sync updated state from backend
      await selectSession(activeSessionId);
      loadSessions();
    } catch (err: any) {
      if (err.name === "AbortError") {
        setStreamingContent((prev) => `${prev}\n\n⚠️ **Execution stopped by user.**`);
      } else {
        console.error("Stream processing error:", err);
        setStreamingContent((prev) => `${prev}\n\n❌ **Error:** ${err.message}`);
      }
    } finally {
      setIsStreaming(false);
      setStreamingThought("");
      setStreamingContent("");
      abortControllerRef.current = null;
    }
  };

  const activeAgent = getAgent(
    sessionState?.activeAgentId || "principal-test-architect"
  );

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-primary)]">
      {/* Claude Code Desktop Style Left Sidebar */}
      <LeftSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewSession={() => createNewSession()}
        onDeleteSession={deleteSession}
        onOpenModelConfig={() => setModelConfigModalOpen(true)}
        onOpenMCPSettings={() => setMcpModalOpen(true)}
        sessionState={sessionState}
        agentsList={agentsList}
        toolsUsed={sessionState?.toolsUsed || {}}
        pluginsList={pluginsList}
        mcpServers={mcpServers}
        isOpen={sidebarOpen}
        onToggleOpen={() => setSidebarOpen(!sidebarOpen)}
        currentModel={currentModel}
        isModelConfigured={isModelConfigured}
        skillsList={skillsList}
        onSelectSkill={(cmd) => handleSendMessage(cmd)}
      />

      {/* Main Center Chat Canvas */}
      <ChatContainer
        sessionName={sessionState?.name || "Agentic QE Campaign"}
        workingDir={sessionState?.workingDir || "workspace"}
        mode={sessionState?.mode || "plan"}
        onToggleMode={handleToggleMode}
        activeAgent={activeAgent}
        onSelectAgent={handleSelectAgent}
        agents={agentsList}
        messages={sessionState?.messages || []}
        streamingThought={streamingThought}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
        onSendMessage={handleSendMessage}
        onStopExecution={handleStopExecution}
        onExportSession={handleExportSession}
        onClearSession={handleClearSession}
        onToggleInspector={() => setInspectorOpen(!inspectorOpen)}
        isInspectorOpen={inspectorOpen}
        currentModel={currentModel}
        isModelConfigured={isModelConfigured}
        onOpenModelConfig={() => setModelConfigModalOpen(true)}
        skills={skillsList}
        onResolveApproval={handleResolveApproval}
      />

      {/* Right Context & Inspector Pane */}
      {sessionState && (
        <ContextInspector
          todos={sessionState.todos}
          ledger={sessionState.ledger}
          gates={sessionState.gates}
          onToggleTodo={handleToggleTodo}
          onAddTodo={handleAddTodo}
          isOpen={inspectorOpen}
          onToggleOpen={() => setInspectorOpen(!inspectorOpen)}
        />
      )}

      {/* Model & System Prompt Config Modal */}
      <ModelConfigModal
        isOpen={modelConfigModalOpen}
        onClose={() => setModelConfigModalOpen(false)}
        onConfigSaved={() => loadConfig()}
      />

      {/* MCP & Plugins Modal */}
      <MCPSettingsModal
        isOpen={mcpModalOpen}
        onClose={() => setMcpModalOpen(false)}
      />
    </div>
  );
}
