"use client";

import React, { useState, useEffect } from "react";
import { X, Settings, Key, Globe, Cpu, FileCode2, Check, AlertCircle } from "lucide-react";
import { Button } from "../harness-ui/Button";
import { Badge } from "../harness-ui/Badge";

interface ModelConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigSaved?: () => void;
}

export const ModelConfigModal: React.FC<ModelConfigModalProps> = ({
  isOpen,
  onClose,
  onConfigSaved,
}) => {
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.openai.com/v1");
  const [model, setModel] = useState("gpt-4o");
  const [customModel, setCustomModel] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [availableModels, setAvailableModels] = useState<string[]>([
    "gpt-4o",
    "gpt-4o-mini",
    "deepseek-chat",
    "deepseek-coder",
    "claude-3-7-sonnet",
    "claude-3-5-sonnet",
    "llama3.3",
    "qwen2.5-coder",
  ]);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetch("/api/config")
        .then((r) => r.json())
        .then((data) => {
          if (data.api_key !== undefined) setApiKey(data.api_key);
          if (data.base_url) setBaseUrl(data.base_url);
          if (data.model) setModel(data.model);
          if (data.system_prompt) setSystemPrompt(data.system_prompt);
          if (data.available_models) setAvailableModels(data.available_models);
        })
        .catch((e) => console.error("Error fetching config:", e));
    }
  }, [isOpen]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);

    const chosenModel = customModel.trim() || model;

    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKey.trim(),
          base_url: baseUrl.trim(),
          model: chosenModel,
          system_prompt: systemPrompt,
          available_models: availableModels,
        }),
      });

      if (res.ok) {
        setSavedSuccess(true);
        if (onConfigSaved) onConfigSaved();
        setTimeout(() => {
          setSavedSuccess(false);
          onClose();
        }, 800);
      }
    } catch (err) {
      console.error("Failed to save config:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleProviderPreset = (provider: "openai" | "deepseek" | "ollama" | "anthropic") => {
    if (provider === "openai") {
      setBaseUrl("https://api.openai.com/v1");
      setModel("gpt-4o");
    } else if (provider === "deepseek") {
      setBaseUrl("https://api.deepseek.com/v1");
      setModel("deepseek-chat");
    } else if (provider === "ollama") {
      setBaseUrl("http://localhost:11434/v1");
      setModel("qwen2.5-coder");
    } else if (provider === "anthropic") {
      setBaseUrl("https://api.anthropic.com/v1");
      setModel("claude-3-7-sonnet");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden text-xs">
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
              <Settings className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-[var(--text-primary)]">
                LLM Provider, Base URL & System Prompt
              </h3>
              <p className="text-[11px] text-[var(--text-muted)] font-mono">
                Real-time API connection for Microsoft Agent Framework Harness
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-[var(--border-color)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-5 flex-1 overflow-y-auto space-y-4 font-mono">
          {/* Presets */}
          <div>
            <label className="text-[11px] text-[var(--text-secondary)] font-semibold block mb-1.5 uppercase tracking-wider">
              Quick Provider Presets
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleProviderPreset("openai")}
                className="px-2.5 py-1 rounded border border-[var(--border-color)] bg-[var(--bg-tertiary)] hover:border-indigo-500 text-[var(--text-primary)] text-xs transition-colors"
              >
                OpenAI (gpt-4o)
              </button>
              <button
                type="button"
                onClick={() => handleProviderPreset("deepseek")}
                className="px-2.5 py-1 rounded border border-[var(--border-color)] bg-[var(--bg-tertiary)] hover:border-indigo-500 text-[var(--text-primary)] text-xs transition-colors"
              >
                DeepSeek (deepseek-chat)
              </button>
              <button
                type="button"
                onClick={() => handleProviderPreset("ollama")}
                className="px-2.5 py-1 rounded border border-[var(--border-color)] bg-[var(--bg-tertiary)] hover:border-indigo-500 text-[var(--text-primary)] text-xs transition-colors"
              >
                Local Ollama / vLLM
              </button>
              <button
                type="button"
                onClick={() => handleProviderPreset("anthropic")}
                className="px-2.5 py-1 rounded border border-[var(--border-color)] bg-[var(--bg-tertiary)] hover:border-indigo-500 text-[var(--text-primary)] text-xs transition-colors"
              >
                Anthropic (Claude)
              </button>
            </div>
          </div>

          {/* Base URL */}
          <div>
            <label className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] font-semibold mb-1">
              <Globe className="w-3.5 h-3.5 text-indigo-400" />
              <span>Base URL (API Endpoint)</span>
            </label>
            <input
              type="text"
              required
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.openai.com/v1 or http://localhost:11434/v1"
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* API Key */}
          <div>
            <label className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] font-semibold mb-1">
              <Key className="w-3.5 h-3.5 text-amber-400" />
              <span>API Key</span>
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-... or leave blank for local Ollama"
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Model Selection */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] font-semibold mb-1">
                <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                <span>Select Model</span>
              </label>
              <select
                value={model}
                onChange={(e) => {
                  setModel(e.target.value);
                  setCustomModel("");
                }}
                className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] text-[var(--text-secondary)] font-semibold mb-1 block">
                Or Custom Model Name
              </label>
              <input
                type="text"
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                placeholder="e.g. deepseek-ai/DeepSeek-V3"
                className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded px-3 py-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Custom System Prompt */}
          <div>
            <label className="flex items-center justify-between text-[11px] text-[var(--text-secondary)] font-semibold mb-1">
              <div className="flex items-center gap-1.5">
                <FileCode2 className="w-3.5 h-3.5 text-indigo-400" />
                <span>Master System Prompt</span>
              </div>
              <Badge variant="outline" size="sm">
                Customizable Prompt
              </Badge>
            </label>
            <p className="text-[10px] text-[var(--text-muted)] font-sans mb-1.5">
              Defines the global behavior of the harness agent and orchestration execution.
            </p>
            <textarea
              rows={4}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-color)] rounded p-2.5 text-xs text-[var(--text-primary)] font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-y"
            />
          </div>

          {/* Footer Actions */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--border-color)]">
            {savedSuccess ? (
              <span className="text-emerald-400 text-xs flex items-center gap-1">
                <Check className="w-3.5 h-3.5" /> Configuration applied successfully!
              </span>
            ) : (
              <span className="text-[10px] text-[var(--text-muted)]">
                Changes persist automatically across sessions.
              </span>
            )}

            <div className="flex gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" loading={saving}>
                Save & Connect
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
