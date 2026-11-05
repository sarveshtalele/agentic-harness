"use client";

import React from "react";
import { Square } from "lucide-react";

interface StopButtonProps {
  onStop: () => void;
  className?: string;
}

export const StopButton: React.FC<StopButtonProps> = ({ onStop, className = "" }) => {
  return (
    <button
      onClick={onStop}
      type="button"
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-mono text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white shadow-lg transition-all animate-pulse ${className}`}
      title="Stop active execution (ESC)"
    >
      <Square className="w-3.5 h-3.5 fill-current" />
      <span>Stop Execution</span>
      <kbd className="ml-1 px-1 py-0.2 rounded bg-rose-800/80 text-[10px] text-rose-100 font-mono">
        ESC
      </kbd>
    </button>
  );
};
