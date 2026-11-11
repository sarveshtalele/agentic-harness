"use client";

import { createContext, ReactNode, useCallback, useContext, useState } from "react";

const ToastContext = createContext<(message: string, tone?: "ok" | "error") => void>(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ message: string; tone: string } | null>(null);
  const show = useCallback((message: string, tone: "ok" | "error" = "ok") => {
    setToast({ message, tone });
    setTimeout(() => setToast(null), 5000);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div role="status" className={`fixed bottom-5 right-5 z-50 max-w-md rounded-lg px-4 py-3 text-sm font-medium text-white shadow-xl ${toast.tone === "error" ? "bg-rose-600" : "bg-emerald-600"}`}>
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}
