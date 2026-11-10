"use client";

import React, { useState, useEffect } from "react";
import { AlertTriangle, Trash2, HelpCircle, Check, X, Loader2 } from "lucide-react";

export interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmText?: string;
  cancelText?: string;
  tone?: "danger" | "primary" | "warning";
  promptPlaceholder?: string;
  promptDefaultValue?: string;
  requirePromptInput?: boolean;
  onConfirm: (inputValue?: string) => void | Promise<void>;
  onClose: () => void;
  busy?: boolean;
}

export function ConfirmModal({
  isOpen,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  tone = "primary",
  promptPlaceholder,
  promptDefaultValue = "",
  requirePromptInput = false,
  onConfirm,
  onClose,
  busy = false,
}: ConfirmModalProps) {
  const [inputValue, setInputValue] = useState(promptDefaultValue);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setInputValue(promptDefaultValue);
      setLoading(false);
    }
  }, [isOpen, promptDefaultValue]);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(inputValue);
      onClose();
    } catch {
      // Handled by caller
    } finally {
      setLoading(false);
    }
  };

  const isDanger = tone === "danger";
  const isWarning = tone === "warning";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
        onClick={!loading && !busy ? onClose : undefined}
      />

      {/* Modal Dialog */}
      <div role="dialog" aria-modal="true" aria-label={title} className="relative w-full max-w-md overflow-hidden rounded-2xl border border-slate-700/60 bg-gradient-to-b from-[#111a33] to-[#0a1122] p-6 text-slate-100 shadow-2xl shadow-indigo-950/50 transition-all animate-in zoom-in-95 duration-200">
        {/* Accent Glow Header */}
        <div className={`absolute top-0 left-0 right-0 h-1 ${isDanger ? 'bg-gradient-to-r from-rose-500 via-red-500 to-amber-500' : isWarning ? 'bg-gradient-to-r from-amber-500 via-orange-500 to-yellow-500' : 'bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500'}`} />

        <div className="flex items-start gap-4">
          <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${isDanger ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30' : isWarning ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30' : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'}`}>
            {isDanger ? <Trash2 className="h-5 w-5" /> : isWarning ? <AlertTriangle className="h-5 w-5" /> : <HelpCircle className="h-5 w-5" />}
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-white tracking-tight">{title}</h3>
            <p className="mt-1.5 text-xs sm:text-sm text-slate-300 leading-relaxed">{description}</p>

            {requirePromptInput && (
              <div className="mt-3.5">
                <input
                  type="text"
                  autoFocus
                  className="w-full rounded-lg border border-slate-700 bg-slate-900/90 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder={promptPlaceholder || "Type value..."}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !loading && !busy) handleConfirm();
                    if (e.key === "Escape" && !loading && !busy) onClose();
                  }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
          <button
            type="button"
            disabled={loading || busy}
            onClick={onClose}
            className="rounded-lg border border-slate-700/80 bg-slate-800/80 px-4 py-2 text-xs sm:text-sm font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-50"
          >
            {cancelText}
          </button>

          <button
            type="button"
            disabled={loading || busy || (requirePromptInput && !inputValue.trim())}
            onClick={handleConfirm}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs sm:text-sm font-medium text-white shadow-lg transition-all disabled:opacity-50 ${
              isDanger
                ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-950/40'
                : isWarning
                ? 'bg-amber-600 hover:bg-amber-500 shadow-amber-950/40'
                : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-950/40'
            }`}
          >
            {(loading || busy) ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                {isDanger ? <Trash2 className="h-4 w-4" /> : <Check className="h-4 w-4" />}
                <span>{confirmText}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
