import type { Metadata } from "next";
import { AuthGate } from "../components/AuthGate";
import { ToastProvider } from "../components/ui";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agentic QE Platform — Agentic BA and QE workspace",
  description: "Requirements, code changes, bug scans, and governed test engineering on Microsoft Agent Framework.",
};

// The person's choice from the theme button wins; until they make one, follow the system setting, also when it changes (UI audit U3).
const themeScript = `(function(){var d=document.documentElement,m=window.matchMedia('(prefers-color-scheme: light)');function chosen(){try{return localStorage.getItem('atlas_theme')}catch(e){return null}}function apply(){var t=chosen()||(m.matches?'light':'dark');d.classList.remove('dark','light');d.classList.add(t)}apply();m.addEventListener('change',function(){if(!chosen())apply()})})()`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="antialiased bg-slate-50 dark:bg-[#030712] text-slate-900 dark:text-slate-100 min-h-screen">
        <ToastProvider><AuthGate>{children}</AuthGate></ToastProvider>
      </body>
    </html>
  );
}
